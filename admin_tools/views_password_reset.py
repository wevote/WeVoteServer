# admin_tools/views_password_reset.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

"""
Password reset for WeVoteServer sign-in (staff, developers and volunteers).
See config/urls.py for the url patterns, and templates/registration/password_reset_*.html.

Notes on the design:
- We deliberately do NOT offer account creation anywhere in this flow. This only resets the
  password of an account that already exists.
- We never reveal whether an email address is attached to an account. Every request ends on the
  same "we sent it if it exists" page, including requests that were rate limited.
- Django's built-in token is single use in practice: the token is built from the user's current
  password hash and last_login, so it stops working once the password is changed.
"""

import hashlib
import logging
import secrets
import time
from urllib.parse import urlsplit

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy

from config.environment_variable_functions import get_environment_variable
from email_outbound.models import EmailAddress
from voter.models import Voter

logger = logging.getLogger(__name__)

# Rate limiting. All counters live in the Django cache (a database cache table), so nothing here
# adds a migration. The design has three goals that pull in different directions: stop brute force
# and enumeration, stop resource exhaustion, and never let one person lock someone else out of
# resetting their own password.
#
# The primary axis is the IP address, not the email address. An email-based hard cap would let an
# attacker burn a victim's allowance and block the victim's own reset, so we do not use one.
RESET_REQUESTS_PER_IP = 10
RESET_RATE_LIMIT_WINDOW_SECONDS = 60 * 60  # one hour

# Send suppression, our email-side protection and the closest thing to a per email rate limit. If we
# already emailed a reset link to an address in this window, we do not send another (the earlier link
# still works), but the request still shows the normal "check your email" page. This stops inbox
# bombing without ever turning the owner away, which a hard per email cap would do. A six minute
# window works out to at most about ten reset emails per hour to any one address, generous enough
# that a flustered user clicking a few times is never penalized.
EMAIL_SEND_SUPPRESS_SECONDS = 6 * 60

# Guessing the emailed link. The token itself is a large HMAC, so this is defense in depth against
# someone hammering the confirm endpoint rather than a real chance of a hit.
CONFIRM_ATTEMPTS_PER_IP = 30

# Cascading ban. When an IP keeps going over a limit, it gets banned for a stretch that doubles each
# time, from a few minutes up to a day. A real user never reaches the second step; an abuser digs a
# deeper and deeper hole. The offense count is remembered for a while so the escalation sticks.
BAN_BASE_SECONDS = 5 * 60
BAN_MAX_SECONDS = 24 * 60 * 60
BAN_OFFENSE_MEMORY_SECONDS = 24 * 60 * 60

# A small fixed delay on each confirm attempt. It slows automated guessing of the emailed link and
# is uniform so it never reveals whether a token was valid. Banned sources are rejected BEFORE this
# delay, so a flood of banned traffic stays cheap to turn away.
DELIBERATE_DELAY_SECONDS = 0.75

# The reset REQUEST endpoint instead runs to a fixed total time (see sleep_until_deadline). For an
# address that has an account we actually send an email, which for a real mail backend takes time;
# for an address that does not, we send nothing. If we simply delayed a fixed amount up front, the
# send time would be added on top and a real account would answer measurably slower, letting an
# attacker tell real addresses from fake ones by timing. Running every request to the same total
# deadline absorbs the send time into the budget so the two are indistinguishable. Must exceed the
# slowest expected send.
RESET_RESPONSE_TARGET_SECONDS = 1.0

SUGGESTED_PASSWORD_LENGTH = 20


def deliberate_delay():
    time.sleep(DELIBERATE_DELAY_SECONDS)


def sleep_until_deadline(started_at):
    """
    Sleep until RESET_RESPONSE_TARGET_SECONDS have passed since started_at, so a reset request takes
    the same total time whether or not an email was sent. If the work already took longer than the
    target, do not sleep. started_at should come from time.monotonic().
    """
    remaining = RESET_RESPONSE_TARGET_SECONDS - (time.monotonic() - started_at)
    if remaining > 0:
        time.sleep(remaining)


def _hashed(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def counter_at_limit(cache_key, limit, window_seconds):
    """
    Fixed window counter. Returns True if this key is already at or above its limit, otherwise
    records one more hit and returns False. A cache problem never blocks a real reset.
    """
    try:
        current_count = cache.get(cache_key)
        if current_count is None:
            cache.set(cache_key, 1, window_seconds)
            return False
        if current_count >= limit:
            return True
        try:
            cache.incr(cache_key)
        except ValueError:
            # The entry expired between the get and the incr.
            cache.set(cache_key, 1, window_seconds)
        return False
    except Exception:
        return False


def is_banned(scope, ip_address):
    """True if this scope ('request' or 'confirm') is currently banned for this IP address."""
    try:
        return cache.get('password_reset_ban_{}_{}'.format(scope, _hashed(ip_address))) is not None
    except Exception:
        # Fail open: a cache problem must never turn a ban we cannot read into a lockout.
        return False


def register_offense(scope, ip_address):
    """
    Record that this IP went over a limit, and (re)apply a ban whose length doubles with each
    offense, capped at BAN_MAX_SECONDS. Called only when a request gets past the ban check while
    over the limit, so the offense count climbs about once per ban rather than once per request.
    """
    offense_key = 'password_reset_offense_{}_{}'.format(scope, _hashed(ip_address))
    try:
        level = cache.get(offense_key)
        if level is None:
            level = 1
            cache.set(offense_key, level, BAN_OFFENSE_MEMORY_SECONDS)
        else:
            try:
                level = cache.incr(offense_key)
            except ValueError:
                level = 1
                cache.set(offense_key, level, BAN_OFFENSE_MEMORY_SECONDS)
        ban_seconds = min(BAN_BASE_SECONDS * (2 ** (level - 1)), BAN_MAX_SECONDS)
        cache.set('password_reset_ban_{}_{}'.format(scope, _hashed(ip_address)), 1, ban_seconds)
    except Exception:
        pass


def email_recently_sent(email_address_text):
    """
    Send suppression. Returns True if we already sent a reset link to this address inside the
    window (so we should not send again). On the first call it claims the slot and returns False.
    Runs the same way whether or not the address has an account, so it never leaks that.
    """
    try:
        cache_key = 'password_reset_sent_{}'.format(_hashed(email_address_text.strip().lower()))
        if cache.get(cache_key) is not None:
            return True
        cache.set(cache_key, 1, EMAIL_SEND_SUPPRESS_SECONDS)
        return False
    except Exception:
        # Fail open: if we cannot read the cache, allow the send rather than block a real reset.
        return False


def generate_suggested_password(length=SUGGESTED_PASSWORD_LENGTH):
    """
    Build a strong password we can offer the person to copy and paste. We leave out characters
    that are easy to confuse with each other (0/O, 1/l/I) so it survives being read off a screen.
    """
    lowercase = 'abcdefghijkmnopqrstuvwxyz'
    uppercase = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
    digits = '23456789'
    punctuation = '!@#$%^&*-_=+'
    alphabet = lowercase + uppercase + digits + punctuation

    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Make sure the suggestion always satisfies the validators we enforce on the form.
        if (any(character in lowercase for character in password) and
                any(character in uppercase for character in password) and
                any(character in digits for character in password) and
                any(character in punctuation for character in password)):
            return password


def get_client_ip_address(request):
    """
    Use REMOTE_ADDR on purpose. X-Forwarded-For can be set by the caller, so trusting it here
    would let anyone slip past the rate limit by making up a new value on each request.
    """
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


class WeVotePasswordResetForm(PasswordResetForm):
    """
    Django looks up the account by Voter.email. People sign in to WeVoteServer with any email
    address that has been verified and linked to their account (see admin_tools.views
    .login_we_vote), so we look those up too. Only verified, non deleted email addresses count.
    """
    def get_users(self, email):
        users = list(super().get_users(email))
        already_found_voter_ids = {voter.pk for voter in users}

        try:
            queryset = EmailAddress.objects.using('readonly').filter(
                normalized_email_address__iexact=email,
                email_ownership_is_verified=True,
                deleted=False,
            )
            voter_we_vote_id_list = list(queryset.values_list('voter_we_vote_id', flat=True))
            print('password_reset get_users: Email found in EmailAddress table')
        except Exception as e:
            print('password_reset get_users: Email not found in EmailAddress table {}'.format(e))
            voter_we_vote_id_list = []

        if voter_we_vote_id_list:
            # Read the Voter from the default database. The token is derived from the current
            # password hash, so a stale replica read could produce a token that does not work.
            linked_voter_queryset = Voter.objects.filter(
                we_vote_id__in=voter_we_vote_id_list,
                is_active=True,
            )
            for voter in linked_voter_queryset:
                if voter.pk not in already_found_voter_ids and voter.has_usable_password():
                    users.append(voter)
                    already_found_voter_ids.add(voter.pk)

        return users


def canonical_link_email_context():
    """
    Build the reset link from the configured WE_VOTE_SERVER_ROOT_URL instead of the incoming Host
    header. Django's default fills the link's domain and protocol from request.get_host(), so a
    forged Host (e.g. evil.example.com) would poison the emailed link and hand the one-time token to
    an attacker. These keys override 'domain'/'protocol' in the reset email context, so the link is
    always our real server regardless of ALLOWED_HOSTS. Returns {} if the URL is missing or
    malformed, which falls back to Django's default rather than breaking the reset.
    """
    try:
        root_url = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
    except Exception:
        root_url = ''
    parts = urlsplit(root_url or '')
    if parts.scheme and parts.netloc:
        return {'domain': parts.netloc, 'protocol': parts.scheme}
    # Failing open here silently restores the Host-header behavior this fix exists to prevent, so make
    # a misconfiguration loud. WE_VOTE_SERVER_ROOT_URL must be set in every deployed environment.
    logger.warning(
        "WV-4734: WE_VOTE_SERVER_ROOT_URL is unset or malformed (%r); password reset links will fall "
        "back to the request Host header, which is vulnerable to reset-link poisoning.", root_url)
    return {}


class WeVotePasswordResetView(auth_views.PasswordResetView):
    """
    Step 1. Ask for the email address and send the single use link.
    """
    form_class = WeVotePasswordResetForm
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    # WV-4734: force the emailed link to use our configured server URL, not the request Host, so a
    # forged Host header cannot poison the reset link. Django merges this over the link context last.
    extra_email_context = canonical_link_email_context()

    def post(self, request, *args, **kwargs):
        ip_address = get_client_ip_address(request)

        # Reject a banned source cheaply, before any timing budget, database, or email work, so a
        # flood cannot tie up workers. Same "check your email" page, so it reveals nothing.
        if is_banned('request', ip_address):
            print('password_reset: request from banned IP {}'.format(ip_address))
            return HttpResponseRedirect(self.get_success_url())

        # Everything past here runs to a fixed total time so an account that exists (which triggers
        # an email send) cannot be told apart from one that does not by timing the response.
        started_at = time.monotonic()

        # Count this attempt per IP. This counts malformed submissions too, so an attacker cannot
        # dodge the limit with junk input. Going over the hourly cap escalates the cascading ban.
        ip_key = 'password_reset_ip_{}'.format(_hashed(ip_address))
        if counter_at_limit(ip_key, RESET_REQUESTS_PER_IP, RESET_RATE_LIMIT_WINDOW_SECONDS):
            register_offense('request', ip_address)
            print('password_reset post: request from IP {} over limit'.format(ip_address))
            response = HttpResponseRedirect(self.get_success_url())
        else:
            print('password_reset post: request from IP posted {}'.format(ip_address))
            response = super().post(request, *args, **kwargs)

        sleep_until_deadline(started_at)
        return response

    def form_valid(self, form):
        # Send suppression instead of a per-email block: if we already emailed this address
        # recently, do not send again, but still show the normal page. The real owner is never
        # locked out; an attacker just cannot bomb one inbox. Claimed before the account lookup,
        # so a real and a nonexistent address behave identically.
        email_address_text = form.cleaned_data.get('email', '')
        if email_address_text and email_recently_sent(email_address_text):
            print('password_reset form_valid: request from IP {} over limit'.format(email_address_text))
            return HttpResponseRedirect(self.get_success_url())
        print('password_reset: form_valid')
        return super().form_valid(form)


class WeVotePasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """
    Step 2. The person arrives from the emailed link and sets a new password twice.
    On success we send them to the sign in page. We do not sign them in automatically, so they
    have to prove they know the new password.
    """
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        # Rate limit and slow down guessing of the emailed link, per IP address. The throttle page
        # is generic, so it never reveals whether the token in the URL was valid.
        ip_address = get_client_ip_address(request)

        # Turn away a banned source cheaply, before the delay.
        if is_banned('confirm', ip_address):
            print('password_reset_confirm: request from banned IP {}'.format(ip_address))
            return render(request, 'registration/password_reset_throttled.html', status=429)

        deliberate_delay()

        ip_key = 'password_reset_confirm_ip_{}'.format(_hashed(ip_address))
        if counter_at_limit(ip_key, CONFIRM_ATTEMPTS_PER_IP, RESET_RATE_LIMIT_WINDOW_SECONDS):
            register_offense('confirm', ip_address)
            return render(request, 'registration/password_reset_throttled.html', status=429)

        print('password_reset_confirm: starting dispatch')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['suggested_password'] = generate_suggested_password()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Your password has been changed. Please sign in with your new password.')
        return response

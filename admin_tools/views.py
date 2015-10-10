from django.shortcuts import render


def admin_home(request):

    template_values = {

    }
    return render(request, 'admin_home/index.html', template_values)

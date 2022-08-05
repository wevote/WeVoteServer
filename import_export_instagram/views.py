from django.http import HttpResponce
from django.shortcuts import render


# Create your views here.
def home_view (*args, **kwargs):
    return HttpResponce("<h1>Hello World!</h1>")
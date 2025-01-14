import os.path

from django.contrib.auth import authenticate
from django.shortcuts import render
from qmpy.models import Entry, Task, Calculation, Formation, MetaData
from .tools import get_globals


def home_page(request):
    data = get_globals()
    data.update(
        {"done": "{:,}".format(Formation.objects.filter(fit="standard").count()),}
    )
    request.session.set_test_cookie()
    return render(request, "index.html", data)


def construction_page(request):
    return render(request, "construction.html", {})


def faq_view(request):
    return render(request, "faq.html")


def play_view(request):
    return render(request, "play.html")


def login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
            else:
                pass
        else:
            pass


def logout(request):
    logout(request)
    # redirect to success

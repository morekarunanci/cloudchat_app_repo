from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from .services import RegisterService


def register_page(request):
    if request.method == "POST":
        data = {
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "username": request.POST.get("username"),
            "email": request.POST.get("email"),
            "password": request.POST.get("password"),
            "dob": request.POST.get("dob"),
        }

        try:
            RegisterService.register(data)
            return redirect("/login/")
        except ValidationError as e:
            return render(request, "register.html", {"error": str(e)})

    return render(request, "register.html")
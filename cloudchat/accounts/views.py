"""
accounts/views.py
-----------------
AWS services used in this file:
  - S3  : export_chat() uploads an Excel file to S3 and returns a pre-signed URL
  - CloudWatch : logger.info/warning calls stream to CloudWatch when deployed on EC2
"""

import random
import io
import logging

from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.http import JsonResponse
from django.db.models import Count, Q
from django.conf import settings as django_settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Profile, Message
from .serializers import RegisterSerializer

import boto3
from django.conf import settings
from datetime import date

# ── CloudWatch / CloudWatch-compatible logger ──────────────────────────────
# In production (EC2 + CLOUDWATCH_ENABLED=1) these log entries appear in the
# CloudWatch Log Group "cloudchat-logs / django-app".
# Locally they print to the console — no code change needed either way.
logger = logging.getLogger('cloudchat_app')


# ═══════════════════════════════════════════════════════════
# API REGISTER (Django REST Framework)
# ═══════════════════════════════════════════════════════════
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"[REGISTER-API] new user via REST: {request.data.get('username')}")
            return Response({"message": "User Registered Successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ═══════════════════════════════════════════════════════════
# REGISTER PAGE
# ═══════════════════════════════════════════════════════════
def register_page(request):
    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name  = request.POST.get('last_name')
        username   = request.POST.get('username')
        email      = request.POST.get('email')
        password   = request.POST.get('password')
        dob        = request.POST.get('dob')

        if not all([first_name, last_name, username, email, password, dob]):
            return render(request, 'register.html', {'error': 'All fields are required'})
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already exists'})
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'Email already exists'})
        if len(password) < 6:
            return render(request, 'register.html', {'error': 'Password must be at least 6 characters'})

        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name=first_name, last_name=last_name
        )
        Profile.objects.create(user=user, dob=dob)
        logger.info(f"[REGISTER] new user registered: {username}")
        return redirect('/login/')

    return render(request, 'register.html')


# ═══════════════════════════════════════════════════════════
# LOGIN PAGE
# ═══════════════════════════════════════════════════════════
def login_page(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            return render(request, 'login.html', {'error': 'All fields are required'})

        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            logger.info(f"[LOGIN] user logged in: {username}")
            return redirect('/dashboard/')
        else:
            logger.warning(f"[LOGIN-FAIL] failed login attempt for: {username}")
            return render(request, 'login.html', {'error': 'Invalid username or password'})

    return render(request, 'login.html')


# ═══════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════
@login_required(login_url='/login/')
def dashboard(request):
    users = User.objects.exclude(id=request.user.id)

    chatted_ids = set()
    for s, r in Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).values_list('sender_id', 'receiver_id'):
        if s != request.user.id:
            chatted_ids.add(s)
        if r != request.user.id:
            chatted_ids.add(r)

    recent_chat_users = User.objects.filter(id__in=chatted_ids)

    return render(request, 'dashboard.html', {
        'users': users,
        'recent_chat_users': recent_chat_users,
    })


# ═══════════════════════════════════════════════════════════
# LOGOUT
# ═══════════════════════════════════════════════════════════
def logout_view(request):
    logger.info(f"[LOGOUT] user logged out: {request.user.username}")
    logout(request)
    return redirect('/login/')


# ═══════════════════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════════════════
@login_required(login_url='/login/')
def profile_page(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        if request.POST.get('delete_image') == "1":
            if profile.profile_image and profile.profile_image.name != 'profile_images/default.png':
                profile.profile_image.delete(save=False)
            profile.profile_image = 'profile_images/default.png'
            profile.save()
            logger.info(f"[PROFILE] {request.user.username} deleted profile image")
        elif request.FILES.get('profile_image'):
            profile.profile_image = request.FILES['profile_image']
            profile.save()
            logger.info(f"[PROFILE] {request.user.username} uploaded new profile image")

    return render(request, 'profile.html', {'profile': profile})


# ═══════════════════════════════════════════════════════════
# FORGOT / OTP / RESET PASSWORD
# ═══════════════════════════════════════════════════════════
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get('email')
        if not User.objects.filter(email=email).exists():
            return render(request, 'forgot_password.html', {'error': 'Email not found'})

        otp = str(random.randint(100000, 999999))
        request.session['reset_email'] = email
        request.session['otp'] = otp

        send_mail(
            'Password Reset OTP - CloudChat',
            f'Your CloudChat OTP is: {otp}',
            'cloudchat@gmail.com',
            [email],
            fail_silently=False,
        )
        logger.info(f"[OTP] password reset OTP sent to: {email}")
        return redirect('/verify-otp/')

    return render(request, 'forgot_password.html')


def verify_otp(request):
    if request.method == "POST":
        user_otp   = request.POST.get('otp')
        session_otp = request.session.get('otp')
        if user_otp == session_otp:
            return redirect('/reset-password/')
        logger.warning(f"[OTP] invalid OTP attempt for: {request.session.get('reset_email')}")
        return render(request, 'verify_otp.html', {'error': 'Invalid OTP'})
    return render(request, 'verify_otp.html')


def reset_password(request):
    if request.method == "POST":
        password         = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if password != confirm_password:
            return render(request, 'reset_password.html', {'error': 'Passwords do not match'})
        email = request.session.get('reset_email')
        user  = User.objects.get(email=email)
        user.set_password(password)
        user.save()
        logger.info(f"[RESET-PW] password reset successfully for: {email}")
        return redirect('/login/')
    return render(request, 'reset_password.html')


# ═══════════════════════════════════════════════════════════
# CHAT — SEND
# ═══════════════════════════════════════════════════════════
@login_required
def send_message(request):
    if request.method == "POST":
        receiver_id = request.POST.get("receiver_id")
        text        = request.POST.get("text", "").strip()

        if not receiver_id or not text:
            return JsonResponse({"error": "receiver_id and text are required"}, status=400)

        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        msg = Message.objects.create(
            sender=request.user,
            receiver=receiver,
            text=text
        )
        logger.info(f"[MSG-SEND] {request.user.username} → {receiver.username} (id={msg.id})")

        return JsonResponse({
            "status": "sent",
            "id":     msg.id,
            "sender": msg.sender.username,
            "text":   msg.text,
            "time":   msg.timestamp.strftime("%H:%M"),
        })

    return JsonResponse({"error": "Invalid request"}, status=400)


# ═══════════════════════════════════════════════════════════
# CHAT — GET MESSAGES
# ═══════════════════════════════════════════════════════════
@login_required
def get_messages(request, user_id):
    try:
        other_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    msg_qs = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user,   receiver=request.user)
    ).order_by('timestamp')

    data = [
        {
            "id":        msg.id,
            "sender":    msg.sender.username,
            "text":      msg.text,
            "time":      msg.timestamp.strftime("%H:%M"),
            "is_mine":   (msg.sender_id == request.user.id),
            "is_edited": msg.is_edited,
        }
        for msg in msg_qs
    ]

    msg_qs.filter(receiver=request.user, is_read=False).update(is_read=True)
    return JsonResponse(data, safe=False)


# ═══════════════════════════════════════════════════════════
# CHAT — UNREAD COUNTS
# ═══════════════════════════════════════════════════════════
@login_required
def unread_counts(request):
    counts = Message.objects.filter(
        receiver=request.user, is_read=False
    ).values('sender__id', 'sender__username').annotate(count=Count('id'))
    return JsonResponse(list(counts), safe=False)


# ═══════════════════════════════════════════════════════════
# CHAT — SEARCH USERS
# ═══════════════════════════════════════════════════════════
@login_required
def search_users(request):
    query = request.GET.get('q', '').strip()
    qs = User.objects.exclude(id=request.user.id)
    if query:
        qs = qs.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
    qs = qs.values('id', 'username', 'first_name', 'last_name')[:30]
    result = [
        {
            "id":        u['id'],
            "username":  u['username'],
            "full_name": f"{u['first_name']} {u['last_name']}".strip() or u['username'],
        }
        for u in qs
    ]
    return JsonResponse(result, safe=False)


# ═══════════════════════════════════════════════════════════
# CHAT — EDIT MESSAGE
# ═══════════════════════════════════════════════════════════
@login_required
def edit_message(request, message_id):
    if request.method == "POST":
        try:
            msg = Message.objects.get(id=message_id, sender=request.user)
        except Message.DoesNotExist:
            return JsonResponse({"error": "Message not found or not yours"}, status=404)

        new_text = request.POST.get("text", "").strip()
        if not new_text:
            return JsonResponse({"error": "Text cannot be empty"}, status=400)

        msg.text      = new_text
        msg.is_edited = True
        msg.save()
        logger.info(f"[MSG-EDIT] user {request.user.username} edited message id={message_id}")

        return JsonResponse({
            "status": "updated",
            "id":     msg.id,
            "text":   msg.text,
            "time":   msg.timestamp.strftime("%H:%M"),
        })

    return JsonResponse({"error": "POST required"}, status=405)


# ═══════════════════════════════════════════════════════════
# CHAT — DELETE MESSAGE
# ═══════════════════════════════════════════════════════════
@login_required
def delete_message(request, message_id):
    if request.method == "POST":
        try:
            msg = Message.objects.get(id=message_id, sender=request.user)
        except Message.DoesNotExist:
            return JsonResponse({"error": "Message not found or not yours"}, status=404)

        msg.delete()
        logger.info(f"[MSG-DELETE] user {request.user.username} deleted message id={message_id}")
        return JsonResponse({"status": "deleted", "id": message_id})

    return JsonResponse({"error": "POST required"}, status=405)


# ═══════════════════════════════════════════════════════════
# SERVICE 3: AWS S3 — Export chat history as Excel
# ═══════════════════════════════════════════════════════════
@login_required
def export_chat(request, user_id):
    """
    Builds an Excel file of the conversation between the logged-in user
    and `user_id`, uploads it to S3, and returns a pre-signed download URL
    that expires in 5 minutes.

    AWS services used:
      - S3  : boto3.client('s3').upload_fileobj() stores the file
      - S3  : generate_presigned_url() creates a temporary secure link
      - IAM : on EC2 the boto3 client uses the instance role automatically
      - CloudWatch : the logger.info call streams to CloudWatch
    """
    try:
        other_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    # ── Build Excel workbook ────────────────────────────────────────────
    try:
        import openpyxl
    except ImportError:
        return JsonResponse({"error": "openpyxl not installed. Run: pip install openpyxl"}, status=500)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Chat History"

    # Header row
    ws.append(["Sender", "Receiver", "Message", "Time", "Edited", "Read"])

    msg_qs = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user,   receiver=request.user)
    ).order_by('timestamp')

    for msg in msg_qs:
        ws.append([
            msg.sender.username,
            msg.receiver.username,
            msg.text,
            msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Yes" if msg.is_edited else "No",
            "Yes" if msg.is_read   else "No",
        ])

    # Save to in-memory buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # ── Upload to S3 ────────────────────────────────────────────────────
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        return JsonResponse({"error": "boto3 not installed. Run: pip install boto3"}, status=500)

    s3_key = f"exports/{request.user.username}_to_{other_user.username}.xlsx"

    try:
        s3 = boto3.client(
            's3',
            region_name            = django_settings.AWS_S3_REGION_NAME,
            aws_access_key_id      = django_settings.AWS_ACCESS_KEY_ID      or None,
            aws_secret_access_key  = django_settings.AWS_SECRET_ACCESS_KEY  or None,
            # On EC2: passing None causes boto3 to auto-use the IAM instance role
        )

        s3.upload_fileobj(
            buffer,
            django_settings.AWS_STORAGE_BUCKET_NAME,
            s3_key,
            ExtraArgs={'ContentType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
        )

        # Pre-signed URL valid for 5 minutes (300 seconds)
        url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': django_settings.AWS_STORAGE_BUCKET_NAME,
                'Key':    s3_key,
            },
            ExpiresIn=300
        )

        logger.info(
            f"[S3-EXPORT] {request.user.username} exported chat with {other_user.username} "
            f"→ s3://{django_settings.AWS_STORAGE_BUCKET_NAME}/{s3_key}"
        )

        return JsonResponse({"download_url": url, "status": "ok"})

    except (BotoCoreError, ClientError) as e:
        logger.warning(f"[S3-EXPORT-FAIL] {request.user.username}: {str(e)}")
        return JsonResponse({"error": f"S3 error: {str(e)}"}, status=500)


import json
import boto3
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Message


@login_required
def export_chats(request):
    user = request.user

    # 🔹 Get all messages (sent + received)
    messages = Message.objects.filter(sender=user) | Message.objects.filter(receiver=user)

    chat_data = []

    for msg in messages.order_by('timestamp'):
        chat_data.append({
            "sender": msg.sender.username,
            "receiver": msg.receiver.username,
            "message": msg.text,
            "timestamp": str(msg.timestamp),
            "is_read": msg.is_read,
            "is_edited": msg.is_edited,
        })

    # 🔹 Convert to JSON
        import json
        import boto3

        # 🔹 Convert to JSON
        json_data = json.dumps(chat_data, indent=4)

        file_name = f"chat_backup_{user.username}.json"

        # 🔹 Upload to S3
        s3 = boto3.client(
            's3',
            region_name='eu-north-1'

        )

        s3.put_object(
            Bucket="erp-exports-cloudchat-app",
            Key=f"exports/{file_name}",
            Body=json_data,
            ContentType='application/json'
        )

    # 🔹 Download response
    response = HttpResponse(json_data, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename={file_name}'

    return response
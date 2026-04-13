from django.urls import path
from . import views
from .views import export_chats
from django.urls import path
from .views import export_chats

urlpatterns = [
    # Chat core
    path('send/',                            views.send_message,   name='send_message'),
    path('get_messages/<int:user_id>/',      views.get_messages,   name='get_messages'),
    path('unread_counts/',                   views.unread_counts,  name='unread_counts'),
    path('search_users/',                    views.search_users,   name='search_users'),

    # CRUD
    path('edit_message/<int:message_id>/',   views.edit_message,   name='edit_message'),
    path('delete_message/<int:message_id>/', views.delete_message, name='delete_message'),

    # AWS S3 — export chat as Excel
    path('export_chat/<int:user_id>/',       views.export_chat,    name='export_chat'),
    path('export-chats/', export_chats, name='export_chats'),
]

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Message
from .forms import MessageForm
from apps.accounts.models import User


@login_required
def inbox(request):
    msgs = Message.objects.filter(receiver=request.user).order_by('-sent_at')
    return render(request, 'communications/inbox.html', {'messages_list': msgs})


@login_required
def send_message(request, receiver_id=None):
    receiver = None
    if receiver_id:
        receiver = get_object_or_404(User, pk=receiver_id)

    form = MessageForm(request.POST or None, user=request.user, initial_receiver=receiver)
    if request.method == 'POST' and form.is_valid():
        msg = form.save(commit=False)
        msg.sender = request.user
        # Basic keyword flagging
        bad_words = ['abuse', 'cheat', 'threat', 'hate', 'stupid', 'idiot', 'fail you']
        body_lower = msg.body.lower()
        for word in bad_words:
            if word in body_lower:
                msg.is_flagged = True
                msg.flag_reason = f"Contains flagged keyword: '{word}'"
                break
        msg.save()
        messages.success(request, 'Message sent!')
        return redirect('inbox')
    return render(request, 'communications/send_message.html', {'form': form, 'receiver': receiver})


@login_required
def message_detail(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    if msg.receiver == request.user and not msg.is_read:
        msg.is_read = True
        msg.save()
    return render(request, 'communications/message_detail.html', {'message': msg})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Message
from .forms import MessageForm
from apps.accounts.models import User
from .utils import keyword_moderate_and_sentiment


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
        mod = keyword_moderate_and_sentiment(msg.body)
        msg.is_flagged = mod.is_flagged
        msg.flag_reason = mod.flag_reason
        msg.sentiment_label = mod.sentiment_label
        msg.sentiment_score = mod.sentiment_score
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


@login_required
def dm_home(request):
    """Teams-like direct messages home: search people + recent threads."""
    # Search people (everyone can DM everyone in this demo)
    q = (request.GET.get('q') or '').strip()
    people_qs = User.objects.exclude(id=request.user.id)

    if q:
        people_qs = people_qs.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)
        )
    people = people_qs.order_by('first_name', 'last_name', 'username')[:20]

    # Recent threads: last message per counterpart (simple Python grouping)
    msgs = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).select_related('sender', 'receiver').order_by('-sent_at')[:200]

    threads = []
    seen = set()
    for m in msgs:
        other = m.receiver if m.sender_id == request.user.id else m.sender
        if other.id in seen:
            continue
        seen.add(other.id)
        threads.append({
            'other': other,
            'last': m,
            'unread': Message.objects.filter(sender=other, receiver=request.user, is_read=False).count(),
        })

    return render(request, 'communications/dm_home.html', {
        'q': q,
        'people': people,
        'threads': threads,
    })


@login_required
def dm_chat(request, user_id: int):
    other = get_object_or_404(User, pk=user_id)
    if other == request.user:
        return redirect('dm_home')

    # Allow chatting with any other user

    thread_qs = Message.objects.filter(
        Q(sender=request.user, receiver=other) | Q(sender=other, receiver=request.user)
    ).select_related('sender', 'receiver').order_by('sent_at')

    # Mark incoming messages as read
    Message.objects.filter(sender=other, receiver=request.user, is_read=False).update(is_read=True)

    if request.method == 'POST':
        body = (request.POST.get('body') or '').strip()
        if body:
            msg = Message(sender=request.user, receiver=other, subject='', body=body)
            mod = keyword_moderate_and_sentiment(body)
            msg.is_flagged = mod.is_flagged
            msg.flag_reason = mod.flag_reason
            msg.sentiment_label = mod.sentiment_label
            msg.sentiment_score = mod.sentiment_score
            msg.save()
        return redirect('dm_chat', user_id=other.id)

    # Left sidebar: recent threads
    recent = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).select_related('sender', 'receiver').order_by('-sent_at')[:200]
    threads = []
    seen = set()
    for m in recent:
        o = m.receiver if m.sender_id == request.user.id else m.sender
        if o.id in seen:
            continue
        seen.add(o.id)
        threads.append({'other': o, 'last': m})

    return render(request, 'communications/dm_chat.html', {
        'other': other,
        'messages_list': thread_qs,
        'threads': threads,
    })


from .models import Channel, ChannelMessage
from .forms import ChannelForm, ChannelMessageForm

@login_required
def channel_list(request):
    channels = request.user.channels.all()
    return render(request, 'communications/channels/list.html', {'channels': channels})

@login_required
def channel_create(request):
    if not request.user.is_teacher():
        messages.error(request, "Only teachers can create channels.")
        return redirect('channel_list')

    form = ChannelForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        channel = form.save(commit=False)
        channel.owner = request.user
        channel.save()
        # Add the selected members plus the owner
        form.save_m2m()
        channel.members.add(request.user)
        messages.success(request, f"Channel '{channel.name}' created!")
        return redirect('channel_detail', pk=channel.pk)
        
    return render(request, 'communications/channels/create.html', {'form': form})

@login_required
def channel_detail(request, pk):
    channel = get_object_or_404(Channel, pk=pk)
    
    # Ensure user is a member
    if request.user not in channel.members.all():
        messages.error(request, "You are not a member of this channel.")
        return redirect('channel_list')
        
    messages_list = channel.messages.select_related('sender').order_by('sent_at')
    channels = request.user.channels.all()
    
    form = ChannelMessageForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        msg = form.save(commit=False)
        msg.channel = channel
        msg.sender = request.user
        mod = keyword_moderate_and_sentiment(msg.body)
        msg.is_flagged = mod.is_flagged
        msg.flag_reason = mod.flag_reason
        msg.sentiment_label = mod.sentiment_label
        msg.sentiment_score = mod.sentiment_score
        msg.save()
        return redirect('channel_detail', pk=channel.pk)

    return render(request, 'communications/channels/detail.html', {
        'channel': channel,
        'messages_list': messages_list,
        'form': form,
        'channels': channels,
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
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


@login_required
def dm_messages_json(request, user_id: int):
    """Return DM thread messages after a given id for lightweight polling."""
    other = get_object_or_404(User, pk=user_id)
    if other == request.user:
        return JsonResponse({'messages': []})

    after_id = request.GET.get('after')
    try:
        after_id_int = int(after_id) if after_id is not None else 0
    except ValueError:
        after_id_int = 0

    qs = Message.objects.filter(
        Q(sender=request.user, receiver=other) | Q(sender=other, receiver=request.user)
    ).select_related('sender').order_by('sent_at', 'id')

    if after_id_int:
        qs = qs.filter(id__gt=after_id_int)

    # Mark incoming messages as read when fetched
    Message.objects.filter(sender=other, receiver=request.user, is_read=False).update(is_read=True)

    payload = []
    for m in qs[:200]:
        payload.append({
            'id': m.id,
            'body': m.body,
            'sender_id': m.sender_id,
            'sender_username': m.sender.username,
            'sent_at': m.sent_at.isoformat() if m.sent_at else None,
            'sent_at_display': m.sent_at.strftime('%d %b, %H:%M') if m.sent_at else '',
            'is_flagged': bool(getattr(m, 'is_flagged', False)),
            'flag_reason': getattr(m, 'flag_reason', '') or '',
        })

    return JsonResponse({'messages': payload})


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


@login_required
def channel_messages_json(request, pk: int):
    """Return channel messages after a given id for lightweight polling."""
    channel = get_object_or_404(Channel, pk=pk)

    if request.user not in channel.members.all():
        return JsonResponse({'messages': []}, status=403)

    after_id = request.GET.get('after')
    try:
        after_id_int = int(after_id) if after_id is not None else 0
    except ValueError:
        after_id_int = 0

    qs = channel.messages.select_related('sender').order_by('sent_at', 'id')
    if after_id_int:
        qs = qs.filter(id__gt=after_id_int)

    payload = []
    for msg in qs[:200]:
        payload.append({
            'id': msg.id,
            'body': msg.body,
            'sender_id': msg.sender_id,
            'sender_name': msg.sender.get_full_name() or msg.sender.username,
            'sent_at': msg.sent_at.isoformat() if msg.sent_at else None,
            'sent_at_display': msg.sent_at.strftime('%d %b %Y, %H:%M') if msg.sent_at else '',
            'is_flagged': bool(getattr(msg, 'is_flagged', False)),
            'flag_reason': getattr(msg, 'flag_reason', '') or '',
            'sentiment_label': getattr(msg, 'sentiment_label', '') or '',
            'sentiment_score': getattr(msg, 'sentiment_score', None),
        })

    return JsonResponse({'messages': payload})

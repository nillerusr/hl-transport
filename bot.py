#!/usr/bin/python3

from threading import Thread
from time import sleep
import time, os, socket, re, sys, traceback, json
import disc
import websocket
import vk
from utils import *
from config import *
from random import randint

servers_disc = { ('127.0.0.1', XASH_PORT): str(DISCORD_CHANNEL_ID) }
servers_vk = { ('127.0.0.1', XASH_PORT): VK_CHAT_ID+2*10**9 }
chats=dict([reversed(i) for i in servers_vk.items()])
channels=dict([reversed(i) for i in servers_disc.items()])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', LOG_PORT))

vkusernames={}
try: vkusernames=json.loads(open('users.json','r').read())
except: None

bot=disc.disc(DISCORD_TOKEN)

bGroup=False
if VK_GROUP_ID: bGroup=True
vkbot=vk.vk(VK_TOKEN, id=VK_GROUP_ID, is_group=bGroup)

def on_event(event):
	if event.t == 'MESSAGE_CREATE' and event.d.channel_id in channels:
		nick=event.d.member._dict['nick']
		if not nick: nick=event.d.author.username
		s='(D)'+nick+': '+event.d.content
		vkbot.send(servers_vk[channels[event.d.channel_id]], s)
		for line in s.split('\n'):
			sock.sendto(b'\xff\xff\xff\xffggm_chat '+line.encode('utf8')+b'\n',channels[event.d.channel_id]);
		print('discord->vk, discord->hl: '+s)

th=Thread(target=bot.gw_loop, args=(on_event,))
th.daemon=True
th.start()

saymatch = re.compile(r'log L \d\d\/\d\d\/\d\d\d\d - \d\d\:\d\d\:\d\d\: "(.*)<\d+><(.*)><\d+>" say "(.*)"')
entermatch = re.compile(r'log L \d\d\/\d\d\/\d\d\d\d - \d\d\:\d\d\:\d\d\: "(.*)<\d+><(.*)><\d+>" entered the game')
disconnectmatch = re.compile(r'log L \d\d\/\d\d\/\d\d\d\d - \d\d\:\d\d\:\d\d\: "(.*)<\d+><(.*)><\d+>" disconnected')
startedmapmatch = re.compile(r'log L \d\d\/\d\d\/\d\d\d\d - \d\d\:\d\d\:\d\d\: Started map "(.*)" \(CRC "0"\)')
servercvarmatch = re.compile(r'log L \d\d\/\d\d\/\d\d\d\d - \d\d\:\d\d\:\d\d\: Server cvar "(.*)" = "(.*)"')
changelevelmatch = re.compile(r'log L \d\d\/\d\d\/\d\d\d\d - \d\d\:\d\d\:\d\d\: CL (.*)')
suicidematch = re.compile(r'log L \d\d\/\d\d\/\d\d\d\d - \d\d\:\d\d\:\d\d\: "(.*)<\d+><(.*)><\d+>" committed suicide with "(.*)"')
waskilledmatch = re.compile(r'log L \d\d\/\d\d\/\d\d\d\d - \d\d\:\d\d\:\d\d\: "(.*)<\d+><(.*)><\d+>" committed suicide with "(.*)" \(.*\)')
killedmatch = re.compile(r'log L \d\d\/\d\d\/\d\d\d\d - \d\d\:\d\d\:\d\d\: "(.*)<\d+><(.*)><\d+>" killed "(.*)<\d+><(.*)><\d+>" with "(.*)"')
ggmmatch = re.compile(r'log L \d\d\/\d\d\/\d\d\d\d - \d\d\:\d\d\:\d\d\: ggm: (.*)')
kickmatch = re.compile(r'log L \d\d\/\d\d\/\d\d\d\d - \d\d\:\d\d\:\d\d\: Kick: "(.*)<\d+><(.*)><>" was kicked by "(.*)" \(message "(.*)"\)')
changematch = re.compile(r'log L \d\d\/\d\d\/\d\d\d\d - \d\d\:\d\d\:\d\d\: "(.*)<\d+><(.*)><\d+>" changed name to "(.*)"')
colorsub = re.compile(r'\^\d')


def longpoll(msg):
	if not msg.type == 'message_new':
		return None

	msg=msg.object
	peer = int(msg['peer_id'])
	if peer in chats.keys():
		fromid = str(msg['from_id'])
		ms=msg['text'].split(' ')
		if ms[0] == '/name':
			newname='(vk)'+' '.join(ms[1:])
			if fromid not in vkusernames.keys():
				vkusernames.update({fromid:newname})
			else:
				vkusernames[fromid] = newname
				vkbot.send(peer, 'Никнейм изменен на: '+newname)
				open('users.json','w').write(json.dumps(vkusernames))
				return None

		name = 'vk unnamed'
		if fromid not in vkusernames.keys():
			if int(fromid) >  0:
				us = vkbot.users.get(user_ids=fromid)['response'][0]
				name = us['first_name'] + ' ' + us['last_name']
			else:
				name = vk.get('groups.getById',group_id=fromid)['response'][0]['name']
				vkusernames.update({fromid:name})
		else: name=vkusernames[fromid]

		text=re.sub('\[club%d\|.*\]'%VK_GROUP_ID, '', msg['text'], 0, 0)
		if not text: return None
		if text[0] == '/' or text[0] == ' ': text=text[1:]
		s = name + ': ' + text
		for line in s.split('\n'):
			sock.sendto(b'\xff\xff\xff\xffggm_chat '+line.encode('utf-8')+b'\n',chats[peer]);
		bot.send(servers_disc[chats[peer]] , s)
		print('vk->discord, vk->hl: '+s)

lpt=Thread(target=vkbot.lp_loop, args=(longpoll,))
lpt.daemon=True
lpt.start()

def say(addr, text):
	bot.send(servers_disc[addr], text)
	vkbot.send(servers_vk[addr], text)
	print('hl->vk, hl->discord: '+text)

while True:
	try:
		l, addr = sock.recvfrom(1024)
		if not addr in servers_disc:
			print(addr, l)
			continue

		l=l[4:].decode('utf8').replace('\\n\'','')
		l = colorsub.sub('', l)
		m = saymatch.match(l)
		if m != None:
			g = m.groups()
			if len(g) == 3:
				text=g[0]+': '+g[2]
				if '@everyone' in text or '@all' in text: continue
				say(addr, text)
			continue

		m = servercvarmatch.match(l)
		if m != None:
			g = m.groups()
			cvars[g[0]] = g[1]
			continue;
		m = startedmapmatch.match(l)
		if m != None:
			g = m.groups()
			text='Map '+g[0]+'started'
			continue
		m = changelevelmatch.match(l)
		if m != None:
			g = m.groups()
			if 'saved position' in g[0]: continue
			text='Changing map: '+g[0]
			say(addr, text)
			continue
		m = suicidematch.match(l)
		if m != None:
			g = m.groups()
			text='\"'+g[0]+'\" commited suicide with '+g[2]
			continue
		m = waskilledmatch.match(l)
		if m != None:
			g = m.groups()
			text='\"'+g[0]+'\" commited suicide with '+g[2]
			continue
		m = killedmatch.match(l)
		if m != None:
			g = m.groups()
			text='\"'+g[0]+'\" kill '+g[2]+' with '+g[4]
			continue
		m = ggmmatch.match(l)
		if m != None:
			g = m.groups() 
			say(addr, g[0])
			continue

		m = kickmatch.match(l)
		if m != None:
			g = m.groups()
			text='Player '+g[0]+' was kicked with message: \"'+g[3]+'\"'
			say(addr, text)
			continue

		m = changematch.match(l)
		if m != None:
			g = m.groups()
			text='Player '+'\"'+g[0]+'\"'+' changed name to: \"'+g[2]+'\"'
			say(addr, text)
			continue

		m = entermatch.match(l)
		if m != None:
			g = m.groups()
			text='Player \"'+g[0]+'\" has joined the game'
			continue

		m = disconnectmatch.match(l)
		if m != None:
			g = m.groups()
			text='Player \"'+g[0]+'\" has left the game'
			continue

	except Exception as e: print(e)

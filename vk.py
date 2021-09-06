# -*- coding: utf-8 -*-
import requests,json,time,random,os,traceback,sys
from utils import *
from colors import *

main_funcs=['call', 'send', 'lp_loop']
class vkmain:
	def __init__(self, token, id, is_group = False):
		self.token = token
		self.is_grp = is_group
		self.lp = None
		self.id = id

	def call(self, method, d={}, **args):
		param = {'v':'5.131','access_token':self.token}
		param.update(d)
		param.update(args)
		ret = requests.post('https://api.vk.com/method/'+method, data=param)
		resp=ret.json()
		if 'error' in resp.keys():
			raise Exception('VkError: '+str(resp['error']))
		return D(resp)

	def send(self, snd, text, attach=None, fwd=0):
		ln=len(text)
		if ln > 4096:
			mess=[]
			for i in range(int(ln/4096)+1):
				time.sleep(1)
				self.call('messages.send',peer_id=snd,message=text[i*4096:(i+1)*4096],random_id=random.randint(0,2**10))
			return True
		else: return self.call('messages.send',peer_id=snd,message=text,attachment=attach,random_id=random.randint(0,2**10))

	def GetLP( self ):
		try:
			if self.is_grp: return self.call('groups.getLongPollServer',lp_version=3,group_id=self.id).response
			else: return self.call('messages.getLongPollServer',lp_version=3)['response']
		except Exception as e:
			print_c(RED+'longpoll error: ')
			traceback.print_exc()
			time.sleep(5)
			return self.GetLP()

	def lp_loop(self, func):
		self.lp = self.GetLP()
		sv = None
		while True:
			try:
				if self.is_grp: sv='%s?act=a_check&key=%s&ts=%s&wait=25&mode=2&version=3'%(self.lp.server, self.lp.key, self.lp.ts)
				else: sv='http://%s?act=a_check&key=%s&ts=%s&wait=25&mode=2&version=3'%(self.lp.server,self.lp.key,self.ts)
				response = D(requests.get(sv).json())
				if response:
					self.lp.ts=response.ts
					for result in response.updates:
						func(result)
			except KeyboardInterrupt:
				print_c(GREEN+'Ctrl+C')
				exit()
			except Exception as e:
				print_c(RED+'error:')
				traceback.print_exc()
				self.lp = self.GetLP( )

class vk:
	class _submethod:
		def __init__(self, vk , name):
			self._name = name
			self._vk = vk
		def __getattr__(self,name):
			def call(d = {},**args):
				d.update(args)
				return self._vk.call(self._name+'.'+name, d)
			return call
	def __init__(self, token, id=0, is_group = False):
		self._vk=vkmain( token, id, is_group )
	def __getattr__(self, name):
		if name in main_funcs:
			return getattr( self._vk, name)
		return self._submethod(self._vk, name)

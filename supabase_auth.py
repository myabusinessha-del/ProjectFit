import json, os, urllib.request, urllib.error
try:
    from projectfit_config import SUPABASE_URL as _URL, SUPABASE_PUBLISHABLE_KEY as _KEY
except Exception:
    _URL, _KEY = '', ''
class SupabaseAuth:
    def __init__(self, url=None, key=None):
        self.url=(url or os.getenv('SUPABASE_URL','') or _URL).rstrip('/')
        self.key=key or os.getenv('SUPABASE_PUBLISHABLE_KEY','') or _KEY
        if not self.url or not self.key:
            raise RuntimeError('SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are required.')
    def _req(self,path,method='GET',body=None,access_token=None):
        data=json.dumps(body).encode() if body is not None else None
        headers={'apikey':self.key,'Content-Type':'application/json'}
        if access_token: headers['Authorization']='Bearer '+access_token
        req=urllib.request.Request(self.url+path,data=data,headers=headers,method=method)
        try:
            with urllib.request.urlopen(req,timeout=15) as r:return json.loads(r.read() or b'{}')
        except urllib.error.HTTPError as e:
            try: msg=json.loads(e.read() or b'{}')
            except Exception: msg={'message':e.reason}
            raise ValueError(msg.get('msg') or msg.get('message') or msg.get('error_description') or 'Supabase request failed.')
    def signup(self,email,password,name=''):
        return self._req('/auth/v1/signup','POST',{'email':email.strip().lower(),'password':password,'data':{'display_name':name.strip()[:80]}})
    def login(self,email,password):
        return self._req('/auth/v1/token?grant_type=password','POST',{'email':email.strip().lower(),'password':password})
    def user(self,access_token): return self._req('/auth/v1/user','GET',access_token=access_token)
    def refresh(self,refresh_token): return self._req('/auth/v1/token?grant_type=refresh_token','POST',{'refresh_token':refresh_token})
    def recover(self,email,redirect_to=None):
        body={'email':email.strip().lower()}
        if redirect_to: body['redirect_to']=redirect_to
        return self._req('/auth/v1/recover','POST',body)
    def logout(self,access_token):
        try:return self._req('/auth/v1/logout','POST',access_token=access_token)
        except Exception:return {'ok':True}

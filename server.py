import json,os,re
from datetime import date
from http.server import BaseHTTPRequestHandler,HTTPServer
from urllib.parse import urlparse,parse_qs
from db import DB
from service import ProjectFit
from auth_service import AuthService
from cloud_service import CloudAccountService
try:
    from projectfit_config import SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY
    os.environ.setdefault('SUPABASE_URL', SUPABASE_URL); os.environ.setdefault('SUPABASE_PUBLISHABLE_KEY', SUPABASE_PUBLISHABLE_KEY)
except Exception: pass
ROOT=os.path.dirname(__file__); db=DB(os.path.join(ROOT,'projectfit.db')); app=ProjectFit(db); app.setup_demo(); auth=AuthService(db)
try: cloud=CloudAccountService(db,app)
except Exception: cloud=None

class Handler(BaseHTTPRequestHandler):
    def json(self,obj,status=200,headers=None):
        data=json.dumps(obj,default=str).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','same-origin'); self.send_header('X-Frame-Options','DENY');
        for k,v in (headers or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(data)
    def do_OPTIONS(self): self.json({},204)
    def body(self): return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0')) or 0) or b'{}')
    def token(self):
        m=re.search(r'(?:^|; )pf_session=([^;]+)',self.headers.get('Cookie','')); return m.group(1) if m else None
    def cloud_token(self):
        m=re.search(r'(?:^|; )pf_cloud_session=([^;]+)',self.headers.get('Cookie','')); return m.group(1) if m else None
    def uid(self,required=True):
        uid=cloud.user_id(self.cloud_token()) if cloud else None
        if not uid: uid=auth.user_from_token(self.token())
        if required and not uid: raise PermissionError('Please log in to continue.')
        return uid
    def do_GET(self):
        u=urlparse(self.path); q=parse_qs(u.query); d=q.get('date',[date.today().isoformat()])[0]
        if u.path in ('/','/index.html'):
            return self.serve('index.html','text/html; charset=utf-8')
        try:
            if u.path=='/api/health': return self.json({'ok':True,'service':'ProjectFit','rule_version':'workbook_v1','app_version':'2.2'})
            if u.path=='/api/cloud/status':
                return self.json({'enabled':bool(cloud),'provider':'Supabase','project_url':os.getenv('SUPABASE_URL','')})
            if u.path=='/api/auth/me':
                uid=self.uid(False); return self.json({'authenticated':bool(uid),'user':app.profile(uid)['user'] if uid else None})
            uid=self.uid()
            if u.path=='/api/home': return self.json(app.home(uid,d))
            if u.path=='/api/programme':
                w,day,rows=app.programme_for(uid,d); return self.json({'week':w,'day':day,'date':d,'exercises':rows,'session':rows[0]['session'] if rows else 'Recovery / optional walk'})
            if u.path=='/api/nutrition': return self.json(app.nutrition(uid,d))
            if u.path=='/api/measurements': return self.json(app.measurements(uid))
            if u.path=='/api/activity': return self.json({'date':d,'entries':app.activities(uid,d)})
            if u.path=='/api/progress': return self.json(app.progress_summary(uid,d))
            if u.path=='/api/review': return self.json(app.progress_review(uid))
            if u.path=='/api/profile': return self.json(app.profile(uid))
            if u.path=='/api/account/export': return self.json(auth.export_user(uid),200,{'Content-Disposition':'attachment; filename="projectfit-data-export.json"'})
            return self.json({'error':'Not found'},404)
        except PermissionError as e:return self.json({'error':str(e)},401)
        except Exception as e:return self.json({'error':str(e)},400)
    def do_POST(self):
        try:
            p=self.body(); path=urlparse(self.path).path
            if path=='/api/auth/cloud/register':
                if not cloud: raise ValueError('Cloud account service is not configured. Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY.')
                r=cloud.signup(p.get('email',''),p.get('password',''),p.get('display_name',''))
                headers={}
                if r.get('session_cookie'): headers['Set-Cookie']=cookie_header('pf_cloud_session',r['session_cookie'])
                return self.json(r,200,headers)
            if path=='/api/auth/cloud/login':
                if not cloud: raise ValueError('Cloud account service is not configured. Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY.')
                r=cloud.login(p.get('email',''),p.get('password','')); return self.json(r,200,{'Set-Cookie':cookie_header('pf_cloud_session',r['session_cookie'])})
            if path=='/api/auth/cloud/recover':
                if not cloud: raise ValueError('Cloud account service is not configured.')
                cloud.auth.recover(p.get('email',''),p.get('redirect_to')); return self.json({'ok':True,'message':'If the account exists, a password-reset email has been sent.'})
            if path=='/api/auth/cloud/logout':
                if cloud: cloud.logout(self.cloud_token())
                return self.json({'ok':True},200,{'Set-Cookie':cookie_header('pf_cloud_session','',expired=True)})
            if path=='/api/auth/cloud/logout-all':
                if not cloud: raise ValueError('Cloud account service is not configured.')
                cloud.logout_all(self.uid()); return self.json({'ok':True},200,{'Set-Cookie':cookie_header('pf_cloud_session','',expired=True)})
            if path=='/api/cloud/sync':
                if not cloud: raise ValueError('Cloud account service is not configured.')
                return self.json(cloud.sync(self.cloud_token()))
            if path=='/api/cloud/pull':
                if not cloud: raise ValueError('Cloud account service is not configured.')
                return self.json(cloud.pull_only(self.cloud_token()))
            if path=='/api/cloud/delete':
                if not cloud: raise ValueError('Cloud account service is not configured.')
                r=cloud.delete_account(self.cloud_token()); return self.json(r,200,{'Set-Cookie':cookie_header('pf_cloud_session','',expired=True)})
            if path=='/api/auth/register':
                uid=auth.register(p.get('email',''),p.get('password',''),p.get('display_name',''))
                token,_,exp=auth.login(p['email'],p['password']); return self.json({'authenticated':True,'user':app.profile(uid)['user']},200,{'Set-Cookie':f'pf_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000'})
            if path=='/api/auth/login':
                token,uid,exp=auth.login(p.get('email',''),p.get('password','')); return self.json({'authenticated':True,'user':app.profile(uid)['user']},200,{'Set-Cookie':cookie_header('pf_session',token)})
            if path=='/api/auth/logout':
                auth.logout(self.token()); return self.json({'ok':True},200,{'Set-Cookie':cookie_header('pf_session','',expired=True)})
            uid=self.uid()
            if path=='/api/auth/logout-all': auth.logout_all(uid); return self.json({'ok':True})
            if path=='/api/auth/migrate-demo': return self.json(app.migrate_demo(uid))
            if path=='/api/auth/delete': auth.delete_user(uid); return self.json({'ok':True},200,{'Set-Cookie':cookie_header('pf_session','',expired=True)})
            routes={'/api/workouts/log':app.log_workout,'/api/nutrition':app.add_nutrition,'/api/nutrition/delete':app.delete_nutrition,'/api/measurements':app.add_measurement,'/api/activity':app.add_activity,'/api/activity/delete':app.delete_activity,'/api/checkins':app.checkin,'/api/profile':app.update_profile,'/api/privacy':app.update_privacy,'/api/planner':app.nutrition_plan,'/api/macro-targets':app.macro_targets}
            if path in routes:return self.json(routes[path](uid,p))
            return self.json({'error':'Not found'},404)
        except PermissionError as e:return self.json({'error':str(e)},401)
        except Exception as e:return self.json({'error':str(e)},400)
    def serve(self,name,ctype):
        path=os.path.join(ROOT,name)
        if not os.path.exists(path):return self.json({'error':'file not found'},404)
        data=open(path,'rb').read(); self.send_response(200); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_HEAD(self):
        u=urlparse(self.path)
        if u.path=='/': return self.serve('index.html','text/html; charset=utf-8')
    def log_message(self,fmt,*args): pass

def cookie_header(name,value,expired=False):
    secure = os.getenv('PROJECTFIT_SECURE_COOKIES','').lower() in ('1','true','yes') or os.getenv('RENDER','').lower()=='true'
    parts=[f'{name}={value}', 'Path=/', 'HttpOnly', 'SameSite=Lax']
    if expired: parts.append('Max-Age=0')
    else: parts.append('Max-Age=2592000')
    if secure: parts.append('Secure')
    return '; '.join(parts)

if __name__=='__main__':
    port=int(os.getenv('PORT','8000'))
    host=os.getenv('HOST','0.0.0.0')
    print(f'ProjectFit running at http://{host}:{port}')
    try: HTTPServer((host,port),Handler).serve_forever()
    except KeyboardInterrupt: print('\nProjectFit server stopped.')

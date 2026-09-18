import json, os, uuid, urllib.request, urllib.error
TABLES=['users','goals','programme','workout_sessions','exercise_logs','workout_derivations','measurements','nutrition_entries','activity_entries','weekly_checkins','weekly_derivations','progress_reviews','privacy_settings']
try:
    from projectfit_config import SUPABASE_URL as _URL, SUPABASE_PUBLISHABLE_KEY as _KEY
except Exception: _URL, _KEY = '', ''
class CloudSync:
    def __init__(self,url=None,key=None):
        self.url=(url or os.getenv('SUPABASE_URL','') or _URL).rstrip('/'); self.key=key or os.getenv('SUPABASE_PUBLISHABLE_KEY','') or _KEY
    def _req(self,path,method='GET',body=None,token=None,prefer='return=representation'):
        data=json.dumps(body).encode() if body is not None else None; h={'apikey':self.key,'Content-Type':'application/json','Prefer':prefer}
        if token:h['Authorization']='Bearer '+token
        req=urllib.request.Request(self.url+path,data=data,headers=h,method=method)
        try:
            with urllib.request.urlopen(req,timeout=20) as r:
                raw=r.read(); return json.loads(raw or b'{}') if raw else {}
        except urllib.error.HTTPError as e:
            try: msg=json.loads(e.read() or b'{}')
            except Exception: msg={'message':e.reason}
            raise ValueError(msg.get('message') or msg.get('error') or 'Cloud sync request failed.')
    def pull(self,uid,token): return self._req('/rest/v1/pf_records?select=id,entity,payload,version,created_at,updated_at,deleted_at&user_id=eq.'+uid+'&order=updated_at.asc','GET',token=token,prefer='')
    def upsert(self,uid,token,rec,base_version):
        rid=rec['id']; cur=self._req('/rest/v1/pf_records?select=id,version,payload,updated_at&user_id=eq.'+uid+'&id=eq.'+rid,'GET',token=token,prefer='')
        if cur:
            cv=int(cur[0]['version'])
            if base_version and base_version!=cv:return None,{'id':rid,'reason':'version_conflict','server':cur[0]}
            nv=cv+1; self._req('/rest/v1/pf_records?id=eq.'+rid+'&user_id=eq.'+uid,'PATCH',{'entity':rec['entity'],'payload':rec['payload'],'version':nv,'deleted_at':rec.get('deleted_at')},token); return {'id':rid,'version':nv},None
        self._req('/rest/v1/pf_records','POST',{'id':rid,'user_id':uid,'entity':rec['entity'],'payload':rec['payload'],'version':1,'deleted_at':rec.get('deleted_at')},token); return {'id':rid,'version':1},None
    def delete_all(self,uid,token): self._req('/rest/v1/pf_records?user_id=eq.'+uid,'DELETE',token=token,prefer='return=minimal')
def table_rows(db,uid):
    out=[]
    for t in TABLES:
        if t=='users': rows=db.q('SELECT * FROM users WHERE id=?',(uid,)).fetchall()
        elif t in ('goals','privacy_settings'): rows=db.q(f'SELECT * FROM {t} WHERE user_id=?',(uid,)).fetchall()
        elif t=='programme': rows=db.q('SELECT * FROM programme WHERE user_id=?',(uid,)).fetchall()
        elif t=='workout_sessions': rows=db.q('SELECT * FROM workout_sessions WHERE user_id=?',(uid,)).fetchall()
        elif t=='exercise_logs': rows=db.q('SELECT el.* FROM exercise_logs el JOIN workout_sessions ws ON ws.id=el.session_id WHERE ws.user_id=?',(uid,)).fetchall()
        elif t=='workout_derivations': rows=db.q('SELECT wd.* FROM workout_derivations wd JOIN exercise_logs el ON el.id=wd.exercise_log_id JOIN workout_sessions ws ON ws.id=el.session_id WHERE ws.user_id=?',(uid,)).fetchall()
        elif t=='weekly_derivations': rows=db.q('SELECT wd.* FROM weekly_derivations wd JOIN weekly_checkins wc ON wc.id=wd.checkin_id WHERE wc.user_id=?',(uid,)).fetchall()
        else: rows=db.q(f'SELECT * FROM {t} WHERE user_id=?',(uid,)).fetchall()
        for r in rows:
            d=dict(r); rid=d.get('id') or d.get('user_id') or d.get('exercise_log_id') or d.get('checkin_id'); stable=str(uuid.uuid5(uuid.NAMESPACE_URL,f'projectfit:{t}:{rid}'))
            out.append({'id':stable,'entity':t,'payload':d})
    return out
def restore_rows(db,uid,records):
    for t in ['privacy_settings','progress_reviews','weekly_derivations','weekly_checkins','activity_entries','nutrition_entries','measurements','workout_derivations','exercise_logs','workout_sessions','programme','goals']:
        if t in ('goals','privacy_settings'): db.q(f'DELETE FROM {t} WHERE user_id=?',(uid,))
        elif t=='weekly_derivations': db.q('DELETE FROM weekly_derivations WHERE checkin_id IN (SELECT id FROM weekly_checkins WHERE user_id=?)',(uid,))
        elif t=='workout_derivations': db.q('DELETE FROM workout_derivations WHERE exercise_log_id IN (SELECT el.id FROM exercise_logs el JOIN workout_sessions ws ON ws.id=el.session_id WHERE ws.user_id=?)',(uid,))
        elif t=='exercise_logs': db.q('DELETE FROM exercise_logs WHERE session_id IN (SELECT id FROM workout_sessions WHERE user_id=?)',(uid,))
        else: db.q(f'DELETE FROM {t} WHERE user_id=?',(uid,))
    order=['users','goals','programme','workout_sessions','exercise_logs','workout_derivations','measurements','nutrition_entries','activity_entries','weekly_checkins','weekly_derivations','progress_reviews','privacy_settings']; by={t:[] for t in order}
    for r in records:
        if r.get('entity') in by: by[r['entity']].append(r['payload'])
    for t in order:
        for d in by[t]:
            cols=list(d); vals=[d[c] for c in cols]; db.q(f"INSERT OR REPLACE INTO {t}({','.join(cols)}) VALUES({','.join('?' for _ in vals)})",vals)
    db.commit()

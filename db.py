import sqlite3, json
from datetime import datetime, timezone
SCHEMA = r"""PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,display_name TEXT NOT NULL,age INTEGER,height_cm REAL,sex TEXT,timezone TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS goals(user_id TEXT PRIMARY KEY,objective TEXT,target_weight REAL,target_body_fat REAL,training_frequency INTEGER,calorie_target REAL DEFAULT 2400,protein_target REAL DEFAULT 180,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS programme(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT NOT NULL,week INTEGER NOT NULL,day TEXT NOT NULL,session TEXT NOT NULL,exercise TEXT NOT NULL,sets INTEGER,rep_range TEXT,start_weight REAL,rir REAL,rest_seconds INTEGER,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS workout_sessions(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,session_date TEXT NOT NULL,week INTEGER NOT NULL,session_name TEXT,status TEXT,notes TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS exercise_logs(id TEXT PRIMARY KEY,session_id TEXT NOT NULL,exercise TEXT NOT NULL,target_sets INTEGER,rep_range TEXT,recommended_kg REAL,actual_kg REAL,reps_json TEXT,avg_rir REAL,form_good TEXT,completed TEXT,notes TEXT,FOREIGN KEY(session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS workout_derivations(exercise_log_id TEXT PRIMARY KEY,recommendation TEXT,estimated_1rm REAL,volume_kg REAL,rule_version TEXT,calculated_at TEXT,FOREIGN KEY(exercise_log_id) REFERENCES exercise_logs(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS measurements(id TEXT PRIMARY KEY,user_id TEXT,measurement_date TEXT,weight REAL,waist REAL,neck REAL,stomach REAL,chest REAL,biceps REAL,quad REAL,calf REAL,manual_bf REAL,calculated_bf REAL,final_bf REAL,seven_day_avg REAL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS nutrition_entries(id TEXT PRIMARY KEY,user_id TEXT,entry_date TEXT,meal TEXT,food TEXT,serving TEXT,calories REAL,protein REAL,carbs REAL,fat REAL,fibre REAL,notes TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS activity_entries(id TEXT PRIMARY KEY,user_id TEXT,activity_date TEXT,activity TEXT,duration_min REAL,distance_km REAL,steps INTEGER,rpe REAL,calories REAL,notes TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS weekly_checkins(id TEXT PRIMARY KEY,user_id TEXT,week INTEGER,checkin_date TEXT,workout_adherence REAL,protein_adherence REAL,calorie_adherence REAL,activity_adherence REAL,checkin_completion REAL,sleep_recovery_component REAL,sleep REAL,energy REAL,soreness REAL,recovery REAL,notes TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS weekly_derivations(checkin_id TEXT PRIMARY KEY,overall_adherence REAL,deload_status TEXT,rule_version TEXT,calculated_at TEXT,FOREIGN KEY(checkin_id) REFERENCES weekly_checkins(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS progress_reviews(id TEXT PRIMARY KEY,user_id TEXT,week INTEGER,review_date TEXT,workout_adherence REAL,metric_d REAL,current_best_strength REAL,historical_max_strength REAL,overall_adherence REAL,review_state TEXT,next_action TEXT,rule_version TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS privacy_settings(user_id TEXT PRIMARY KEY,consent INTEGER,sharing_enabled INTEGER,deletion_requested INTEGER,updated_at TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS auth_credentials(user_id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,email_verified INTEGER DEFAULT 0,password_hash TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS auth_sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,created_at TEXT NOT NULL,expires_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_ws_user_date ON workout_sessions(user_id,session_date);
CREATE INDEX IF NOT EXISTS idx_m_user_date ON measurements(user_id,measurement_date);
CREATE INDEX IF NOT EXISTS idx_n_user_date ON nutrition_entries(user_id,entry_date);
CREATE TABLE IF NOT EXISTS cloud_sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,access_token TEXT NOT NULL,refresh_token TEXT,created_at TEXT NOT NULL,expires_at TEXT,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS cloud_record_state(record_id TEXT PRIMARY KEY,server_version INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_cloud_sessions_user ON cloud_sessions(user_id);
"""
class DB:
    def __init__(self,path="projectfit.db"):
        self.c=sqlite3.connect(path); self.c.row_factory=sqlite3.Row; self.c.executescript(SCHEMA)
    def now(self): return datetime.now(timezone.utc).isoformat()
    def q(self,sql,args=()): return self.c.execute(sql,args)
    def commit(self): self.c.commit()
    def close(self): self.c.close()

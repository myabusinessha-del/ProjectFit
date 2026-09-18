import math,re
RULE_VERSION='workbook_v1'
MAIN_LIFTS={'Barbell Bench Press','Barbell Squat','Romanian Deadlift','Barbell Bent-over Row','Barbell Row','DB Shoulder Press'}
def _number(v):
    if v is None or v=='': return None
    try:
        n=float(v); return n if math.isfinite(n) else None
    except: return None
def parse_rep_range(s):
    if not s: return None,None
    m=re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)',str(s))
    if m:return float(m.group(1)),float(m.group(2))
    m=re.search(r'(\d+(?:\.\d+)?)',str(s))
    return (float(m.group(1)),None) if m else (None,None)
def workout_recommendation(completed,reps,form,rir,rep_range):
    if completed!='Yes': return ''
    vals=[_number(x) for x in (reps or [])]; vals=[x for x in vals if x is not None]
    if not vals:return ''
    if form=='No':return 'REDUCE WEIGHT'
    rir=_number(rir)
    if rir is None:return 'KEEP WEIGHT'
    lo,hi=parse_rep_range(rep_range); mn=min(vals)
    if lo is None:return 'INCREASE REPS'
    if rir<=0 and mn<lo:return 'REDUCE WEIGHT'
    if mn<lo:return 'KEEP WEIGHT'
    if hi is not None and mn>=hi and rir>=1.5:return 'INCREASE WEIGHT'
    return 'INCREASE REPS'
def estimated_1rm(exercise,kg,reps):
    kg=_number(kg); vals=[_number(x) for x in (reps or [])]; vals=[x for x in vals if x is not None]
    if exercise not in MAIN_LIFTS or kg is None or kg<=0 or not vals or max(vals)<=0:return None
    return kg*(1+max(vals)/30)
def training_volume(kg,reps,completed):
    kg=_number(kg); vals=[_number(x) for x in (reps or [])]; vals=[x for x in vals if x is not None]
    return kg*sum(vals) if completed=='Yes' and kg is not None else 0
def seven_day_weight_average(weights):
    vals=[_number(x) for x in weights]; vals=[x for x in vals if x is not None and x>0]
    return sum(vals)/len(vals) if vals else None
def body_fat_calculated(waist,neck,height_cm,sex):
    waist,neck,height_cm=map(_number,(waist,neck,height_cm))
    if waist is None or neck is None or height_cm is None or sex!='Male' or waist<=neck or height_cm<=0:return None
    return (495/(1.0324-0.19077*math.log10(waist-neck)+0.15456*math.log10(height_cm))-450)/100
def final_body_fat(manual,calc):
    return _number(manual) if _number(manual) is not None else _number(calc)
def daily_nutrition(entries):
    t={k:0.0 for k in ('calories','protein','carbs','fat','fibre')}
    for e in entries:
        if not e.get('meal') or not e.get('food'):continue
        c=_number(e.get('calories'))
        if c is None or c<=0:continue
        t['calories']+=c
        for k in t:
            if k!='calories':t[k]+=_number(e.get(k)) or 0
    return t
def weekly_adherence(w,p,c,a,ci,sr):
    vals=[_number(x) for x in (w,p,c,a,ci,sr)]
    if any(x is None for x in vals):return None
    w,p,c,a,ci,sr=vals
    return .30*w+.25*p+.15*c+.10*a+.10*ci+.10*sr
def deload_status(vals,workout):
    nums=[_number(x) for x in vals]
    if len([x for x in nums if x is not None])<4 or len(vals)<4:return 'REVIEW DATA'
    h,i,j,k=nums[:4]; c=_number(workout)
    if None in (h,i,j,k,c):return 'REVIEW DATA'
    return 'CONSIDER DELOAD' if ((h+i+k)/3)<5 and j>=8 and c<75 else 'NORMAL TRAINING'
def progress_review(c,d,current,historical,h):
    vals=[_number(x) for x in (c,d,current,historical,h)]
    if sum(x is not None for x in vals)<3:return 'REVIEW DATA'
    c,d,current,historical,h=vals
    if None not in (c,d,current,historical) and c<100 and d<98 and current>=historical:return 'POSITIVE RECOMPOSITION'
    if h is not None and h>=80:return 'ON TRACK'
    return 'MONITOR'
def progress_recommendation(state,h,c,d):
    h,c,d=_number(h),_number(c),_number(d)
    if state=='POSITIVE RECOMPOSITION':return 'STAY COURSE'
    if h is not None and h<70:return 'REVIEW RECOVERY'
    if c is not None and d is not None and c>=100 and d>=98:return 'INCREASE ACTIVITY'
    return 'STAY COURSE'
def programme_week(start,current):
    w=(current-start).days//7+1
    return max(1,min(12,w))

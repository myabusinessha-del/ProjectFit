from math import ceil, isfinite
CATALOG = [
    {'id':'oats','name':'Oats','unit_g':1000,'price':45,'kcal':389,'protein':16.9,'carbs':66.3,'fat':6.9,'fibre':10.6,'stores':['Checkers','Pick n Pay','Woolworths']},
    {'id':'eggs','name':'Eggs','unit_g':24*50,'price':70,'kcal':143,'protein':12.6,'carbs':0.7,'fat':9.5,'fibre':0,'stores':['Checkers','Pick n Pay','Woolworths']},
    {'id':'chicken','name':'Chicken breast','unit_g':1500,'price':150,'kcal':120,'protein':22.5,'carbs':0,'fat':2.6,'fibre':0,'stores':['Checkers','Pick n Pay','Woolworths']},
    {'id':'mince','name':'Lean beef mince','unit_g':500,'price':90,'kcal':176,'protein':26,'carbs':0,'fat':8,'fibre':0,'stores':['Checkers','Pick n Pay','Woolworths']},
    {'id':'tuna','name':'Tuna','unit_g':170,'price':18,'kcal':116,'protein':26,'carbs':0,'fat':0.8,'fibre':0,'stores':['Checkers','Pick n Pay','Woolworths']},
    {'id':'rice','name':'Rice','unit_g':2000,'price':45,'kcal':360,'protein':7.1,'carbs':79.3,'fat':0.7,'fibre':1.3,'stores':['Checkers','Pick n Pay','Woolworths']},
    {'id':'potato','name':'Potatoes','unit_g':2500,'price':45,'kcal':77,'protein':2,'carbs':17.5,'fat':0.1,'fibre':2.2,'stores':['Checkers','Pick n Pay','Woolworths']},
    {'id':'frozenveg','name':'Frozen mixed vegetables','unit_g':1000,'price':40,'kcal':60,'protein':3,'carbs':10,'fat':0.5,'fibre':3.5,'stores':['Checkers','Pick n Pay','Woolworths']},
    {'id':'banana','name':'Bananas','unit_g':1000,'price':30,'kcal':89,'protein':1.1,'carbs':22.8,'fat':0.3,'fibre':2.6,'stores':['Checkers','Pick n Pay','Woolworths']},
    {'id':'peanut','name':'Peanut butter','unit_g':800,'price':55,'kcal':588,'protein':25,'carbs':20,'fat':50,'fibre':6,'stores':['Checkers','Pick n Pay','Woolworths']},
    {'id':'milk','name':'Low-fat milk','unit_g':2000,'price':40,'kcal':46,'protein':3.4,'carbs':4.8,'fat':1.5,'fibre':0,'stores':['Checkers','Pick n Pay','Woolworths']},
    {'id':'whey','name':'Whey protein','unit_g':1000,'price':450,'kcal':400,'protein':75,'carbs':10,'fat':7,'fibre':0,'stores':['Checkers','Pick n Pay','Woolworths']},
]
MEALS = [
    ('Breakfast','Protein oats', [('oats',70),('milk',250),('banana',100),('peanut',10)]),
    ('Breakfast','Egg oats', [('eggs',150),('oats',50),('banana',100)]),
    ('Lunch','Chicken rice bowl', [('chicken',180),('rice',100),('frozenveg',200)]),
    ('Lunch','Tuna rice bowl', [('tuna',170),('rice',100),('frozenveg',200)]),
    ('Dinner','Chicken potato bowl', [('chicken',180),('potato',300),('frozenveg',200)]),
    ('Dinner','Mince potato bowl', [('mince',180),('potato',300),('frozenveg',200)]),
    ('Snack','Whey banana shake', [('whey',35),('banana',100),('milk',200)]),
    ('Snack','Egg peanut snack', [('eggs',100),('peanut',15),('banana',100)]),
]
VEGETARIAN_MEALS = {
    'lunch': ('Lunch', 'Egg rice bowl', [('eggs',150),('rice',100),('frozenveg',200)]),
    'dinner': ('Dinner', 'Egg and potato bowl', [('eggs',150),('potato',300),('frozenveg',200)]),
}


def _validated_number(value, label, minimum=None, strict_minimum=False):
    if isinstance(value, bool):
        raise ValueError(f'{label} must be a valid number.')
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{label} must be a valid number.')
    if not isfinite(number):
        raise ValueError(f'{label} must be a finite number.')
    if minimum is not None:
        invalid = number <= minimum if strict_minimum else number < minimum
        if invalid:
            qualifier = 'greater than' if strict_minimum else 'at least'
            raise ValueError(f'{label} must be {qualifier} {minimum}.')
    return number

def _validated_days(value):
    if isinstance(value, bool):
        raise ValueError('Days must be a whole number between 1 and 14.')
    try:
        days_number = float(value)
    except (TypeError, ValueError):
        raise ValueError('Days must be a whole number between 1 and 14.')
    if not isfinite(days_number) or not days_number.is_integer():
        raise ValueError('Days must be a whole number between 1 and 14.')
    days = int(days_number)
    if days < 1 or days > 14:
        raise ValueError('Days must be between 1 and 14.')
    return days


def validate_plan_request_payload(payload):
    """Validate raw API values before the service layer coerces them."""
    for field, label in (
        ('calories', 'Calorie target'),
        ('protein', 'Protein target'),
        ('budget', 'Budget'),
    ):
        if isinstance(payload.get(field), bool):
            raise ValueError(f'{label} must be a valid number.')

    if 'days' in payload and payload['days'] not in (None, ''):
        _validated_days(payload['days'])


def validate_macro_target_payload(payload):
    """Validate optional demographic numbers before service-layer conversion."""
    for field, label in (
        ('age', 'Age'),
        ('height_cm', 'Height'),
        ('weight_kg', 'Weight'),
    ):
        if field in payload and payload[field] not in (None, ''):
            _validated_number(payload[field], label, 0, strict_minimum=True)


def calc_food(items):
    out={k:0.0 for k in ('calories','protein','carbs','fat','fibre')}
    for item,g in items:
        c=next(x for x in CATALOG if x['id']==item); f=g/100
        out['calories']+=c['kcal']*f; out['protein']+=c['protein']*f; out['carbs']+=c['carbs']*f; out['fat']+=c['fat']*f; out['fibre']+=c['fibre']*f
    return out


def cost_for(items):
    total=0
    for item,g in items:
        c=next(x for x in CATALOG if x['id']==item); total += g/c['unit_g']*c['price']
    return total


def add_scaled(target, meals):
    return [{'meal':meal_name,'name':meal_name,'items':list(meal_items)} for meal_name,meal_items in meals]


def calculate_targets(age,height_cm,weight_kg,sex,activity,goal):
    age = _validated_number(age, 'Age', 0, strict_minimum=True)
    height_cm = _validated_number(height_cm, 'Height', 0, strict_minimum=True)
    weight_kg = _validated_number(weight_kg, 'Weight', 0, strict_minimum=True)

    sex_key = str(sex or '').strip().lower()
    if sex_key in ('male', 'm'):
        s = 5
    elif sex_key in ('female', 'f'):
        s = -161
    else:
        raise ValueError('Sex must be Male or Female for this calculation.')

    factors={'sedentary':1.2,'light':1.375,'moderate':1.55,'high':1.725,'very_high':1.9}
    activity_key = str(activity or '').strip().lower()
    if activity_key not in factors:
        raise ValueError('Activity must be one of: sedentary, light, moderate, high, very_high.')

    adj={'lose':0.80,'recomp':0.90,'maintain':1.0,'gain':1.10}
    goal_key = str(goal or '').strip().lower()
    if goal_key not in adj:
        raise ValueError('Goal must be one of: lose, recomp, maintain, gain.')

    bmr=10*weight_kg+6.25*height_cm-5*age+s
    tdee=bmr*factors[activity_key]; calories=round(tdee*adj[goal_key]/50)*50
    protein=round(max(1.6,2.0 if goal_key in ('lose','recomp') else 1.6)*weight_kg/5)*5
    fat=round(max(0.7*weight_kg, calories*0.25/9)/5)*5
    carbs=max(0,round((calories-protein*4-fat*9)/4/5)*5)
    return {'bmr':round(bmr),'tdee':round(tdee),'calories':calories,'protein':protein,'carbs':carbs,'fat':fat,'fibre':30,'method':'Mifflin-St Jeor + activity/goal adjustment; planning estimate'}


def plan_for(calories, protein, budget, meals_per_day=4, days=7, vegetarian=False, use_whey=True):
    calories = _validated_number(calories, 'Calorie target', 0, strict_minimum=True)
    protein = _validated_number(protein, 'Protein target', 0)

    days = _validated_days(days)

    if isinstance(budget, bool):
        raise ValueError('Budget must be a non-negative number.')
    try:
        budget = float(budget)
    except (TypeError, ValueError):
        raise ValueError('Budget must be a non-negative number.')
    if not isfinite(budget) or budget < 0:
        raise ValueError('Budget must be a non-negative number.')

    choices={'breakfast':MEALS[0] if use_whey else MEALS[1],'lunch':MEALS[2],'dinner':MEALS[4],'snack':MEALS[6] if use_whey else MEALS[7]}
    if vegetarian: choices.update(VEGETARIAN_MEALS)
    try:
        meals_per_day = int(meals_per_day)
    except (TypeError, ValueError):
        meals_per_day = 4
    if meals_per_day not in (3, 4, 5):
        meals_per_day = 4

    def meal_entry(key):
        meal, name, items = choices[key]
        return {'meal': meal, 'name': name, 'items': list(items)}

    breakfast = meal_entry('breakfast')
    lunch = meal_entry('lunch')
    snack = meal_entry('snack')
    dinner = meal_entry('dinner')

    if meals_per_day == 3:
        breakfast['name'] += ' + snack'
        breakfast['items'].extend(snack['items'])
        base = [breakfast, lunch, dinner]
    elif meals_per_day == 5:
        if use_whey:
            snack_one = {'meal': 'Snack', 'name': 'Whey shake', 'items': [('whey', 35), ('milk', 200)]}
            snack_two = {'meal': 'Snack', 'name': 'Banana snack', 'items': [('banana', 100)]}
        else:
            snack_one = {'meal': 'Snack', 'name': 'Egg and peanut snack', 'items': [('eggs', 100), ('peanut', 15)]}
            snack_two = {'meal': 'Snack', 'name': 'Banana snack', 'items': [('banana', 100)]}
        base = [breakfast, lunch, snack_one, snack_two, dinner]
    else:
        base = [breakfast, lunch, snack, dinner]

    protein_adjustment_meal = base[0] if meals_per_day == 3 else base[2]
    macros=calc_food([(i,g) for m in base for i,g in m['items']])
    if macros['protein'] < protein:
        if vegetarian:
            protein_food, protein_per_gram, adjustment_meal = 'eggs', 0.126, base[-1]
        else:
            protein_food, protein_per_gram, adjustment_meal = 'chicken', 0.225, base[1]
        extra=max(0,(protein-macros['protein'])/protein_per_gram)
        adjustment_meal['items'].append((protein_food,min(150,extra)))
        macros=calc_food([(i,g) for m in base for i,g in m['items']])
    if macros['protein'] < protein and use_whey:
        extra=max(0,(protein-macros['protein'])/0.75); protein_adjustment_meal['items'].append(('whey',min(35,extra))); macros=calc_food([(i,g) for m in base for i,g in m['items']])
    remaining=max(0,calories-macros['calories'])
    if remaining:
        base[1]['items'].append(('rice',min(180,remaining/3.6))); macros=calc_food([(i,g) for m in base for i,g in m['items']]); remaining=max(0,calories-macros['calories'])
        if remaining: base[-1]['items'].append(('potato',min(250,remaining/0.77)))
    macros=calc_food([(i,g) for m in base for i,g in m['items']]); fat_gap=max(0,70-macros['fat'])
    if fat_gap:
        pb=min(50,fat_gap/0.5); base[0]['items'].append(('peanut',pb)); added=pb*5.88
        for idx,(food,g) in enumerate(base[1]['items']):
            if food=='rice': base[1]['items'][idx]=(food,max(0,g-added/3.6)); break
    daily=[]
    for m in base:
        fm=calc_food(m['items']); daily.append({'meal':m['meal'],'name':m['name'],'items':[{'food':next(c['name'] for c in CATALOG if c['id']==i),'grams':round(g,0)} for i,g in m['items']],**fm})
    daily_tot={k:sum(m[k] for m in daily) for k in ('calories','protein','carbs','fat','fibre')}
    weekly={}
    for m in daily:
        for x in m['items']: weekly[x['food']]=weekly.get(x['food'],0)+x['grams']*days
    shopping=[]
    for name,grams in weekly.items():
        c=next(c for c in CATALOG if c['name']==name); packs=ceil(grams/c['unit_g'])
        shopping.append({'food':name,'required_g':round(grams),'pack_g':c['unit_g'],'packs':packs,'price_per_pack':c['price'],'estimated_cost':round(packs*c['price'],2),'stores':c['stores']})
    total_cost=sum(x['estimated_cost'] for x in shopping)
    budget_for_plan = budget * days / 7
    target_comparison = {}
    for key, target in (('calories', calories), ('protein', protein)):
        actual = round(daily_tot[key], 1)
        target_value = round(target, 1)
        target_comparison[key] = {
            'target': target_value,
            'actual': actual,
            'difference': round(actual - target_value, 1),
        }

    return {
        'targets': {'calories': calories, 'protein': protein, 'budget': budget},
        'days': days,
        'meals_per_day': len(daily),
        'daily': daily,
        'daily_totals': daily_tot,
        'target_comparison': target_comparison,
        'shopping': shopping,
        'estimated_total': round(total_cost, 2),
        'budget': budget,
        'budget_for_plan': round(budget_for_plan, 2),
        'budget_status': 'WITHIN BUDGET' if total_cost <= budget_for_plan else 'OVER BUDGET',
        'catalogue_note': 'Weekly budget is prorated to the selected plan duration. Prices are planning estimates; verify current pack prices and availability in-store/online.',
    }
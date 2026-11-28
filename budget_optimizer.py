from copy import deepcopy
from math import ceil, isfinite

from planner import CATALOG, calc_food, build_shopping_item

CATALOG_BY_ID = {item['id']: item for item in CATALOG}
CATALOG_BY_NAME = {item['name']: item for item in CATALOG}
MACRO_KEYS = ('calories', 'protein', 'carbs', 'fat', 'fibre')


def _unchanged(plan, reason):
    result = deepcopy(plan)
    result['budget_optimization'] = {'applied': False, 'reason': reason}
    return result


def optimize_budget_plan(plan):
    """Apply the opt-in protein substitution without materially worsening targets.

    The swap preserves daily protein to within 0.5 g, limits calorie change to
    2%, and checks any additional macro targets supplied by the profile.
    Shopping costs are recalculated using full catalogue packs.
    """
    if not isinstance(plan, dict):
        raise ValueError('A generated meal plan is required.')

    if plan.get('budget_optimization', {}).get('applied'):
        return deepcopy(plan)

    daily = plan.get('daily')
    if not isinstance(daily, list) or not daily:
        return _unchanged(plan, 'Daily meal details are unavailable.')

    rebuilt = []
    changes = []
    for meal in daily:
        if not isinstance(meal, dict) or not isinstance(meal.get('items'), list):
            return _unchanged(plan, 'A meal has an invalid ingredient list.')

        pairs = []
        displayed_items = []
        changed = False
        for item in meal['items']:
            if not isinstance(item, dict):
                return _unchanged(plan, 'An ingredient entry is invalid.')
            catalogue_item = CATALOG_BY_NAME.get(item.get('food'))
            if catalogue_item is None:
                return _unchanged(plan, 'An ingredient is not in the current food catalogue.')
            try:
                grams = float(item.get('grams'))
            except (TypeError, ValueError):
                return _unchanged(plan, 'An ingredient quantity is invalid.')
            if not isfinite(grams) or grams < 0:
                return _unchanged(plan, 'An ingredient quantity is invalid.')

            if catalogue_item['id'] == 'whey':
                replacement = CATALOG_BY_ID['pea_protein']
                replacement_grams = round(
                    grams * catalogue_item['protein'] / replacement['protein'], 1
                )
                pairs.append((replacement['id'], replacement_grams))
                displayed_items.append({
                    'food': replacement['name'],
                    'grams': replacement_grams,
                })
                changes.append({
                    'from': catalogue_item['name'],
                    'to': replacement['name'],
                    'grams_before': grams,
                    'grams_after': replacement_grams,
                })
                changed = True
            else:
                pairs.append((catalogue_item['id'], grams))
                displayed_items.append({'food': catalogue_item['name'], 'grams': item['grams']})

        macros = calc_food(pairs)
        meal_name = meal.get('name', '')
        if changed and isinstance(meal_name, str):
            meal_name = meal_name.replace('Whey', 'Pea protein').replace('whey', 'pea protein')
        rebuilt.append({
            **meal,
            'name': meal_name,
            'items': displayed_items,
            **macros,
        })

    if not changes:
        return _unchanged(plan, 'This plan has no whey-protein ingredient to replace.')

    original_totals = plan.get('daily_totals')
    if not isinstance(original_totals, dict):
        return _unchanged(plan, 'Original daily nutrition totals are unavailable.')

    new_totals = {
        key: sum(float(meal.get(key, 0) or 0) for meal in rebuilt)
        for key in MACRO_KEYS
    }
    try:
        original_calories = float(original_totals['calories'])
        original_protein = float(original_totals['protein'])
        original_cost = float(plan['estimated_total'])
        days_value = plan['days']
        if isinstance(days_value, bool):
            raise ValueError
        days_number = float(days_value)
    except (KeyError, TypeError, ValueError):
        return _unchanged(plan, 'Original plan totals or duration are unavailable.')

    if (
        not isfinite(original_calories) or original_calories <= 0
        or not isfinite(original_protein) or original_protein < 0
        or not isfinite(original_cost) or original_cost < 0
        or not isfinite(days_number) or not days_number.is_integer()
        or days_number < 1 or days_number > 14
    ):
        return _unchanged(plan, 'Original plan totals or duration are invalid.')

    calorie_change = abs(new_totals['calories'] - original_calories) / original_calories
    protein_change = abs(new_totals['protein'] - original_protein)
    if calorie_change > 0.02 or protein_change > 0.5:
        return _unchanged(
            plan,
            'The substitution would change daily calories or protein beyond the safe tolerance.',
        )

    targets = plan.get('targets')
    if isinstance(targets, dict):
        for key in ('carbs', 'fat', 'fibre'):
            if key not in targets:
                continue
            try:
                target = float(targets[key])
                original_actual = float(original_totals[key])
            except (KeyError, TypeError, ValueError):
                return _unchanged(
                    plan,
                    f'The original {key} target or nutrition total is unavailable.',
                )
            if (
                not isfinite(target) or target < 0
                or not isfinite(original_actual)
            ):
                return _unchanged(
                    plan,
                    f'The original {key} target or nutrition total is invalid.',
                )
            tolerance = max(1.0, abs(target) * 0.02)
            original_gap = abs(original_actual - target)
            optimized_gap = abs(new_totals[key] - target)
            if optimized_gap > original_gap + tolerance:
                return _unchanged(
                    plan,
                    f'The substitution would materially worsen the {key} target.',
                )

    required_by_id = {}
    for meal in rebuilt:
        for item in meal['items']:
            catalogue_item = CATALOG_BY_NAME[item['food']]
            required_by_id[catalogue_item['id']] = (
                required_by_id.get(catalogue_item['id'], 0)
                + float(item['grams']) * int(days_number)
            )

    shopping = []
    for item_id, required_grams in required_by_id.items():
        catalogue_item = CATALOG_BY_ID[item_id]
        shopping.append(build_shopping_item(catalogue_item, required_grams))

    optimized_cost = round(sum(item['estimated_cost'] for item in shopping), 2)
    if optimized_cost >= original_cost:
        return _unchanged(plan, 'No lower full-pack purchase cost was found.')

    result = deepcopy(plan)
    result['daily'] = rebuilt
    result['daily_totals'] = new_totals
    result['shopping'] = shopping
    result['estimated_total'] = optimized_cost

    budget_for_plan = plan.get('budget_for_plan')
    try:
        budget_limit = float(budget_for_plan)
        if isfinite(budget_limit) and budget_limit >= 0:
            result['budget_status'] = (
                'WITHIN BUDGET' if optimized_cost <= budget_limit else 'OVER BUDGET'
            )
    except (TypeError, ValueError):
        pass

    targets = plan.get('targets')
    if isinstance(targets, dict):
        comparison = plan.get('target_comparison')
        comparison = deepcopy(comparison) if isinstance(comparison, dict) else {}
        for key in MACRO_KEYS:
            if key not in targets:
                continue
            try:
                target = float(targets[key])
            except (TypeError, ValueError):
                continue
            if not isfinite(target) or target < 0:
                continue
            actual = round(new_totals[key], 1)
            target_value = round(target, 1)
            comparison[key] = {
                'target': target_value,
                'actual': actual,
                'difference': round(actual - target_value, 1),
            }
        if comparison:
            result['target_comparison'] = comparison

    result['budget_optimization'] = {
        'applied': True,
        'changes': changes,
        'original_estimated_total': round(original_cost, 2),
        'optimized_estimated_total': optimized_cost,
        'estimated_savings': round(original_cost - optimized_cost, 2),
        'calorie_change_percent': round(
            (new_totals['calories'] - original_calories) / original_calories * 100, 2
        ),
        'protein_change_grams': round(new_totals['protein'] - original_protein, 2),
        'note': (
            'Estimated full-pack purchase savings. Check pea-protein ingredients and '
            'allergen information before use.'
        ),
    }
    return result

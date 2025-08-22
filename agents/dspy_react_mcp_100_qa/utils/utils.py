from typing import List, Dict

def get_cost_from_history(history: List[Dict]) -> Dict: 
    '''
    Calculate the cost and usage from a dspy.LM.history object.
    
    Args:
        history: dspy.LM.history object 
        
    Returns:
        A dictionary containing the total cost and usage.
    '''
    total_cost = 0
    total_usage = {}
    
    for item in history:
        total_cost += item["cost"]
        item_usage = item["usage"]
        for key, value in item_usage.items():
            if key not in total_usage:
                total_usage[key] = 0
            if value is None or total_usage[key] is None:
                total_usage[key] = None
            else:
                print(value, total_usage[key])
                total_usage[key] += value
       
    all_cost_info = {"cost": total_cost, "usage": total_usage} 
    return all_cost_info
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
        
        # Convert usage object to dict if it's not already
        if hasattr(item_usage, 'model_dump'):
            item_usage = item_usage.model_dump()
        elif hasattr(item_usage, '__dict__'):
            item_usage = dict(item_usage.__dict__)
        elif not isinstance(item_usage, dict):
            # Fallback: try to convert to dict
            try:
                item_usage = dict(item_usage)
            except (TypeError, ValueError):
                # If conversion fails, skip this item's usage
                continue
        
        for key, value in item_usage.items():
            if key not in total_usage:
                total_usage[key] = 0
            if value is None or total_usage[key] is None:
                total_usage[key] = None
            else:
                # Ensure value is a number before adding
                if isinstance(value, (int, float)):
                    total_usage[key] += value
                else:
                    # If it's not a number, we can't sum it
                    total_usage[key] = str(value)  # Convert to string for storage
       
    all_cost_info = {"cost": total_cost, "usage": total_usage} 
    return all_cost_info
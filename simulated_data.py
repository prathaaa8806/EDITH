# data/simulated_data.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_queue_data(days=30):
    """
    30 din ka fake queue data generate karega
    Jaise real bank/hospital mein hota hai
    """
    data = []
    start_date = datetime.now() - timedelta(days=days)
    
    for day in range(days):
        current_date = start_date + timedelta(days=day)
        day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
        
        # Har ghante ka data (9 AM to 5 PM = working hours)
        for hour in range(9, 17):
            # --- REALISTIC PATTERNS ---
            
            # Monday aur Friday pe zyada bheed hoti hai
            if day_of_week in [0, 4]:  # Monday, Friday
                base_people = random.randint(15, 35)
            # Wednesday moderate
            elif day_of_week == 2:
                base_people = random.randint(10, 25)
            # Sunday band (ya kam)
            elif day_of_week == 6:
                base_people = random.randint(2, 8)
            else:
                base_people = random.randint(8, 22)
            
            # Lunch time pe rush hota hai (12-2 PM)
            if 12 <= hour <= 14:
                base_people = int(base_people * 1.5)
            
            # Subah 9-10 bhi rush hota hai
            if hour == 9:
                base_people = int(base_people * 1.3)
            
            # Month start pe zyada log aate hain (salary, bills)
            if current_date.day <= 5:
                base_people = int(base_people * 1.4)
            
            # 3 counters ke liye data
            for counter_id in range(1, 4):
                # Har counter pe alag log
                people = max(1, base_people + random.randint(-5, 5))
                
                # Service time per person (minutes)
                avg_service_time = random.uniform(3, 8)
                
                # Waiting time = log * avg service time / counters
                wait_time = round((people * avg_service_time) / 3, 1)
                
                data.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'hour': hour,
                    'day_of_week': day_of_week,
                    'day_name': current_date.strftime('%A'),
                    'counter_id': counter_id,
                    'people_in_queue': people,
                    'avg_service_time_min': round(avg_service_time, 1),
                    'estimated_wait_time_min': wait_time,
                    'is_month_start': 1 if current_date.day <= 5 else 0,
                    'is_lunch_hour': 1 if 12 <= hour <= 14 else 0,
                    'total_people_all_counters': base_people * 3
                })
    
    df = pd.DataFrame(data)
    df.to_csv('data/historical_queue_data.csv', index=False)
    print(f"✅ {len(df)} rows ka data generate ho gaya!")
    print(f"📅 {days} din ka data hai")
    print(df.head(10))
    return df

if __name__ == "__main__":
    generate_queue_data(60)  # 60 din ka data
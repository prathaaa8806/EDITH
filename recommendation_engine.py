# engine/recommendation_engine.py

class RecommendationEngine:
    """
    AI Queue Manager - Dynamic recommendations for any number of counters.
    Balances load, predicts bottlenecks, and suggests exact actions.
    """

    def __init__(self):
        self.max_acceptable_wait = 15
        self.max_people_per_counter = 12

    def analyze_and_recommend(self, counter_data):
        """
        counter_data: list of dicts, supports ANY number of counters
        [{'counter_id': 1, 'people': 18, 'wait_time': 32}, ...]
        """
        recommendations = []
        warnings = []
        total_counters = len(counter_data)

        if total_counters == 0:
            return {
                'total_people': 0, 'average_wait_time': 0,
                'busiest_counter': '-', 'least_busy_counter': '-',
                'best_counter_for_new_customer': '-',
                'warnings': ["⚠️ No active counters!"],
                'recommendations': ["Activate at least 1 counter."],
                'status': 'CRITICAL'
            }

        total_people = sum(c['people'] for c in counter_data)
        avg_wait = sum(c['wait_time'] for c in counter_data) / total_counters
        capacity = self.max_people_per_counter * total_counters

        sorted_counters = sorted(counter_data, key=lambda x: x['people'])
        min_counter = sorted_counters[0]
        max_counter = sorted_counters[-1]

        # --- RULE 1: Per-Counter Overload ---
        for c in counter_data:
            if c['people'] > self.max_people_per_counter:
                excess = c['people'] - self.max_people_per_counter
                warnings.append(
                    f"🔴 Counter {c['counter_id']} OVERLOADED: "
                    f"{c['people']} people ({excess} excess). "
                    f"Wait: {c['wait_time']} min."
                )

        # --- RULE 2: Smart Load Balancing (Exact Numbers) ---
        difference = max_counter['people'] - min_counter['people']
        if difference >= 6:
            shift = difference // 2
            recommendations.append(
                f"🔄 REDIRECT {shift} people from Counter {max_counter['counter_id']} "
                f"→ Counter {min_counter['counter_id']}. "
                f"(Gap: {difference} people)"
            )

        # --- RULE 3: Open New Counters ---
        if total_people > capacity:
            extra = max(1, (total_people - capacity + self.max_people_per_counter - 1) // self.max_people_per_counter)
            recommendations.append(
                f"🆕 OPEN {extra} NEW COUNTER(S)! "
                f"Current: {total_counters} counters handling {total_people} people "
                f"(capacity: {capacity})."
            )

        # --- RULE 4: Fast-Track / Express Queue ---
        critical = [c['counter_id'] for c in counter_data if c['wait_time'] > 30]
        if critical:
            recommendations.append(
                f"⏰ FAST-TRACK NEEDED: Counter(s) {critical} have >30 min wait. "
                f"Open express counter for quick queries."
            )

        # --- RULE 5: Staff Reallocation ---
        idle = [c['counter_id'] for c in counter_data if c['people'] <= 3]
        busy = [c['counter_id'] for c in counter_data if c['people'] > 15]
        if idle and busy:
            recommendations.append(
                f"👥 STAFF SHIFT: Move 1 staff from Counter {idle[0]} "
                f"(idle, {sorted_counters[0]['people']} people) "
                f"to Counter {busy[0]} (overloaded)."
            )

        # --- RULE 6: All Good ---
        if not recommendations and not warnings:
            recommendations.append(
                "✅ OPTIMAL: All queues balanced. No action needed."
            )

        # --- Dynamic Status ---
        utilization = total_people / capacity if capacity > 0 else 0
        if utilization > 1.2:
            status = 'CRITICAL'
        elif utilization > 0.9:
            status = 'HIGH'
        elif utilization > 0.6:
            status = 'MODERATE'
        else:
            status = 'NORMAL'

        return {
            'total_people': total_people,
            'average_wait_time': round(avg_wait, 1),
            'busiest_counter': max_counter['counter_id'],
            'least_busy_counter': min_counter['counter_id'],
            'best_counter_for_new_customer': min_counter['counter_id'],
            'utilization_pct': round(utilization * 100, 1),
            'warnings': warnings,
            'recommendations': recommendations,
            'status': status
        }
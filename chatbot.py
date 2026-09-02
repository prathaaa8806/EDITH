# engine/chatbot.py
import re

class QueueChatBot:
    def __init__(self):
        self.counter_data = []
        self.result = {}

    def update_data(self, counter_data, result):
        """Feed live data on every render"""
        self.counter_data = counter_data
        self.result = result

    def respond(self, query):
        q = query.lower().strip()

        if not self.counter_data:
            return "⚠️ No live data available yet. Please turn ON the camera or provide manual input first."

        # ── 1. Specific Counter Query ──
        c_match = re.search(
            r'counter\s*(\d+)|c[- ]?(\d+)|(\d+)\s*(?:number|no)', q
        )
        if c_match:
            c_num = int(c_match.group(1) or c_match.group(2) or c_match.group(3))
            return self._counter_specific(c_num, q)

        # ── 2. Least Queue ──
        if any(w in q for w in [
            'least', 'min', 'minimum', 'short', 'shortest',
            'free', 'empty', 'quick', 'fast', 'lowest', 'less'
        ]):
            return self._least_queue()

        # ── 3. Busiest / Most ──
        if any(w in q for w in [
            'most', 'max', 'maximum', 'busiest', 'crowd', 'crowded',
            'full', 'heavy', 'highest', 'longest', 'busy'
        ]):
            return self._busiest()

        # ── 4. Total People ──
        if any(w in q for w in [
            'total', 'how many people', 'overall count', 'sum',
            'all people', 'combined', 'aggregate'
        ]):
            return self._total()

        # ── 5. Wait Time ──
        if any(w in q for w in [
            'wait', 'waiting', 'how long', 'duration',
            'time', 'delay', 'eta'
        ]):
            return self._wait_general()

        # ── 6. Status ──
        if any(w in q for w in [
            'status', 'condition', 'situation', 'how is',
            'what is happening', 'current state', 'overview'
        ]):
            return self._status()

        # ── 7. Recommendation ──
        if any(w in q for w in [
            'recommend', 'suggest', 'where should', 'which counter',
            'route', 'best counter', 'send', 'direct', 'advice'
        ]):
            return self._recommendation()

        # ── 8. Compare ──
        if any(w in q for w in ['compare', 'vs', 'versus', 'better', 'difference']):
            return self._compare(q)

        # ── 9. All Summary ──
        if any(w in q for w in [
            'all', 'summary', 'overview', 'entire', 'full report', 'details'
        ]):
            return self._all_summary()

        # ── 10. Greetings ──
        if any(w in q for w in [
            'hi', 'hello', 'hey', 'hola', 'sup', 'yo', 'greetings'
        ]):
            return (
                "👋 Hey! I'm the QAdapt AI Assistant.\n"
                "Ask me anything about live queues, for example:\n"
                '• *"Where is the queue shortest?"*\n'
                '• *"What is the wait time at Counter 2?"*\n'
                '• *"What is the overall status?"*'
            )

        # ── Default ──
        return self._default()

    # ════════════════════════════════════════
    #  PRIVATE RESPONSE BUILDERS
    # ════════════════════════════════════════

    def _counter_specific(self, c_num, q):
        found = [c for c in self.counter_data if c['counter_id'] == c_num]
        if not found:
            return f"❌ No data found for Counter {c_num}. Active counters: 1 to {len(self.counter_data)}"

        c = found[0]
        tag = "🔴 OVERLOADED" if c['people'] > 15 else "🟡 BUSY" if c['people'] > 8 else "🟢 NORMAL"

        if any(w in q for w in ['wait', 'time', 'duration', 'how long']):
            return (
                f"⏱️ **Counter {c_num}** estimated wait time: "
                f"**~{c['wait_time']} minutes**\n"
                f"(Currently {c['people']} people in line)"
            )

        return (
            f"📊 **Counter {c_num} Live Status:**\n"
            f"- 👥 Queue: **{c['people']} people**\n"
            f"- ⏱️ Wait: **~{c['wait_time']} min**\n"
            f"- Signal: {tag}"
        )

    def _least_queue(self):
        lightest = min(self.counter_data, key=lambda x: x['people'])
        return (
            f"✅ **Shortest queue is at Counter {lightest['counter_id']}!**\n"
            f"- 👥 Only **{lightest['people']} people**\n"
            f"- ⏱️ Wait: **~{lightest['wait_time']} min**\n\n"
            f"👉 Send new arrivals here for quickest service!"
        )

    def _busiest(self):
        busiest = max(self.counter_data, key=lambda x: x['people'])
        return (
            f"🔴 **Highest queue is at Counter {busiest['counter_id']}!**\n"
            f"- 👥 **{busiest['people']} people** in line\n"
            f"- ⏱️ Wait: **~{busiest['wait_time']} min**\n\n"
            f"⚠️ Avoid this counter if possible!"
        )

    def _total(self):
        total = sum(c['people'] for c in self.counter_data)
        return (
            f"👥 **Total {total} people** across all counters "
            f"({len(self.counter_data)} counters currently active)."
        )

    def _wait_general(self):
        avg = self.result.get('average_wait_time', 0)
        best = min(self.counter_data, key=lambda x: x['wait_time'])
        worst = max(self.counter_data, key=lambda x: x['wait_time'])
        return (
            f"⏱️ **Wait Time Overview:**\n"
            f"- Average: **~{avg} min**\n"
            f"- 🟢 Shortest: **Counter {best['counter_id']} (~{best['wait_time']} min)**\n"
            f"- 🔴 Longest: **Counter {worst['counter_id']} (~{worst['wait_time']} min)**"
        )

    def _status(self):
        emoji = {'NORMAL': '🟢', 'MODERATE': '🟡', 'HIGH': '🟠', 'CRITICAL': '🔴'}
        s = self.result.get('status', 'UNKNOWN')
        return (
            f"{emoji.get(s, '⚪')} **Overall Status: {s}**\n"
            f"- 👥 Total Queue: **{self.result.get('total_people', 0)}**\n"
            f"- 📊 Utilization: **{self.result.get('utilization_pct', 0)}%**\n"
            f"- ⏱️ Avg Wait: **{self.result.get('average_wait_time', 0)} min**"
        )

    def _recommendation(self):
        best = self.result.get('best_counter_for_new_customer', '?')
        recs = self.result.get('recommendations', [])
        rec_text = "\n".join([f"  • {r}" for r in recs[:3]])
        return (
            f"💡 **AI Recommendation:**\n"
            f"📍 Route new customers to **Counter {best}**!\n\n"
            f"**Quick Tips:**\n{rec_text}"
        )

    def _compare(self, q):
        nums = re.findall(r'\d+', q)
        if len(nums) >= 2:
            c1, c2 = int(nums[0]), int(nums[1])
            d1 = [c for c in self.counter_data if c['counter_id'] == c1]
            d2 = [c for c in self.counter_data if c['counter_id'] == c2]
            if d1 and d2:
                winner = c1 if d1[0]['people'] < d2[0]['people'] else c2
                return (
                    f"⚔️ **Counter {c1} vs Counter {c2}:**\n"
                    f"- C{c1}: 👥 {d1[0]['people']} people | ⏱️ ~{d1[0]['wait_time']} min\n"
                    f"- C{c2}: 👥 {d2[0]['people']} people | ⏱️ ~{d2[0]['wait_time']} min\n\n"
                    f"🏆 **Counter {winner} is the better choice!**"
                )
        return (
            "🤔 Please specify two counter numbers to compare.\n"
            'Example: *"Compare counter 1 and 3"*'
        )

    def _all_summary(self):
        lines = ["📋 **All Counters Live Summary:**\n"]
        for c in self.counter_data:
            e = "🔴" if c['people'] > 15 else "🟡" if c['people'] > 8 else "🟢"
            lines.append(
                f"  {e} **Counter {c['counter_id']}**: "
                f"{c['people']} people | ~{c['wait_time']} min wait"
            )
        lines.append(f"\n👥 **Total: {sum(c['people'] for c in self.counter_data)} people**")
        return "\n".join(lines)

    def _default(self):
        return (
            "🤖 I can instantly answer your queue-related queries! Try asking:\n\n"
            '• *"Where is the queue shortest?"*\n'
            '• *"What is the wait time at Counter 2?"*\n'
            '• *"How many people are there in total?"*\n'
            '• *"Which is the best counter right now?"*\n'
            '• *"What is the overall status?"*\n'
            '• *"Compare counter 1 vs 3"*\n'
            '• *"Give me a summary of all counters"*'
        )
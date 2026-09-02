# models/queue_predictor.py
import importlib
sklearn_model_selection = importlib.import_module('sklearn.model_selection')
train_test_split = sklearn_model_selection.train_test_split
sklearn_metrics = importlib.import_module('sklearn.metrics')
mean_absolute_error = sklearn_metrics.mean_absolute_error
r2_score = sklearn_metrics.r2_score
import pickle
import os
import warnings
warnings.filterwarnings('ignore')

# Load pandas dynamically so static analysis does not require its source stub.
pd = importlib.import_module('pandas')
np = importlib.import_module('numpy')
sklearn_ensemble = importlib.import_module('sklearn.ensemble')
RandomForestRegressor = sklearn_ensemble.RandomForestRegressor
GradientBoostingRegressor = sklearn_ensemble.GradientBoostingRegressor

class QueuePredictor:
    """
    ML Engine: Predicts queue buildup and wait times using
    Gradient Boosting (people) + Random Forest (wait time).
    """

    def __init__(self):
        self.model = None
        self.wait_time_model = None
        self.is_trained = False
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _ensure_dirs(self):
        os.makedirs(os.path.join(self.root_dir, 'models'), exist_ok=True)
        os.makedirs(os.path.join(self.root_dir, 'data'), exist_ok=True)

    def _csv_path(self):
        return os.path.join(self.root_dir, 'data', 'historical_queue_data.csv')

    def _model_path(self, name):
        return os.path.join(self.root_dir, 'models', name)

    def load_and_prepare_data(self):
        csv = self._csv_path()
        if not os.path.exists(csv):
            raise FileNotFoundError(f"CSV not found at {csv}")
        df = pd.read_csv(csv)
        features = ['hour', 'day_of_week', 'counter_id', 'is_month_start', 'is_lunch_hour']
        X = df[features]
        y_people = df['people_in_queue']
        y_wait = df['estimated_wait_time_min']
        return X, y_people, y_wait, df

    def train(self):
        self._ensure_dirs()
        print("🚶‍♂️‍➡️ Training ML models...")

        try:
            X, y_people, y_wait, df = self.load_and_prepare_data()
        except FileNotFoundError:
            from data.simulated_data import generate_queue_data
            generate_queue_data(60)
            X, y_people, y_wait, df = self.load_and_prepare_data()

        # Model 1: People Count
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_people, test_size=0.2, random_state=42
        )
        self.model = GradientBoostingRegressor(
            n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42
        )
        self.model.fit(X_train, y_train)
        mae = mean_absolute_error(y_test, self.model.predict(X_test))
        r2 = r2_score(y_test, self.model.predict(X_test))
        print(f"   People Model → MAE: {mae:.2f}, R²: {r2:.4f}")

        # Model 2: Wait Time
        X_train2, X_test2, y_train2, y_test2 = train_test_split(
            X, y_wait, test_size=0.2, random_state=42
        )
        self.wait_time_model = RandomForestRegressor(
            n_estimators=150, max_depth=8, random_state=42
        )
        self.wait_time_model.fit(X_train2, y_train2)
        w_mae = mean_absolute_error(y_test2, self.wait_time_model.predict(X_test2))
        print(f"   Wait Model   → MAE: {w_mae:.2f} min")

        self.is_trained = True
        self.save_model()
        print("✅ Models trained & saved!")
        return mae, r2

    def predict_queue(self, hour, day_of_week, counter_id,
                      is_month_start=0, is_lunch_hour=0):
        if not self.is_trained:
            self.load_model()

        # Safe mapping: if counter_id > 3, map to 1-3 cycle
        safe_cid = ((counter_id - 1) % 3) + 1

        inp = np.array([[hour, day_of_week, safe_cid, is_month_start, is_lunch_hour]])
        people = max(1, int(round(self.model.predict(inp)[0])))
        wait = max(1, round(self.wait_time_model.predict(inp)[0], 1))
        return people, wait

    def predict_future(self, current_hour, day_of_week,
                       is_month_start=0, minutes_ahead=20, active_counters=3):
        future_hour = current_hour + (minutes_ahead / 60)

        if future_hour >= 18 or future_hour < 9:
            return {
                'total_predicted_people': 0,
                'alert_message': "⚪ Facility closed during this time window.",
                'predictions': []
            }

        is_lunch = 1 if 12 <= future_hour <= 14 else 0
        predictions = []

        for c in range(1, active_counters + 1):
            people, wait = self.predict_queue(
                int(future_hour), day_of_week, c, is_month_start, is_lunch
            )
            predictions.append({
                'counter': c,
                'predicted_people': people,
                'predicted_wait_min': wait
            })

        total = sum(p['predicted_people'] for p in predictions)
        threshold = 10 * active_counters

        if total > threshold * 1.3:
            alert = (f"🚨 CRITICAL: Queue will exceed {total} people "
                     f"in {minutes_ahead} mins! Immediate action required.")
        elif total > threshold:
            alert = (f"⚠️ WARNING: Queue likely to exceed {total} people "
                     f"within the next {minutes_ahead} minutes.")
        else:
            alert = (f"✅ STABLE: ~{total} people expected "
                     f"in {minutes_ahead} mins. Normal operations.")

        return {
            'future_time_minutes': minutes_ahead,
            'total_predicted_people': total,
            'alert_message': alert,
            'predictions': predictions
        }

    def save_model(self):
        self._ensure_dirs()
        with open(self._model_path('people_model.pkl'), 'wb') as f:
            pickle.dump(self.model, f)
        with open(self._model_path('wait_model.pkl'), 'wb') as f:
            pickle.dump(self.wait_time_model, f)

    def load_model(self):
        try:
            with open(self._model_path('people_model.pkl'), 'rb') as f:
                self.model = pickle.load(f)
            with open(self._model_path('wait_model.pkl'), 'rb') as f:
                self.wait_time_model = pickle.load(f)
            self.is_trained = True
        except FileNotFoundError:
            print("⚠️ Models not found. Training from scratch...")
            self.train()
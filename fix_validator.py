
path = 'titan/execution/validator.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """        if not issues and required_capital is not None:
            issues.extend(self._check_funds_available(broker, required_capital))
            issues.extend(self._check_margin_available(broker, required_capital))"""

replacement1 = """        if not issues and required_capital is not None:
            issues.extend(self._check_funds_available(broker, required_capital))
            issues.extend(self._check_margin_available(broker, required_capital))
            
        if not issues:
            issues.extend(self._check_position_limits(broker, plan))
            issues.extend(self._check_daily_loss(broker))"""

content = content.replace(target1, replacement1)

target2 = """    def _check_margin_available(self, broker: Broker, required: Decimal) -> list[str]:
        try:
            margin = broker.margin()
            if margin.available_margin < required:
                return [f"Insufficient margin. Required: {required}, Available: {margin.available_margin}"]
            return []
        except Exception as e:
            return [f"Failed to check margin: {e}"]"""

replacement2 = """    def _check_margin_available(self, broker: Broker, required: Decimal) -> list[str]:
        try:
            margin = broker.margin()
            if margin.available_margin < required:
                return [f"Insufficient margin. Required: {required}, Available: {margin.available_margin}"]
            return []
        except Exception as e:
            return [f"Failed to check margin: {e}"]

    def _check_position_limits(self, broker: Broker, plan: ExecutionPlan) -> list[str]:
        try:
            positions = broker.positions()
            for order in plan.orders:
                # Basic limit check placeholder logic
                pos = next((p for p in positions if p.symbol == order.symbol), None)
                current_qty = pos.quantity if pos else 0
                new_qty = current_qty + order.quantity
                if abs(new_qty) > 500: # Arbitrary hard limit for safety
                    return [f"Position limit exceeded for {order.symbol}. New qty: {new_qty}, Limit: 500"]
            return []
        except Exception as e:
            return [f"Failed to check position limits: {e}"]

    def _check_daily_loss(self, broker: Broker) -> list[str]:
        try:
            positions = broker.positions()
            total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
            if total_unrealized_pnl < -100000: # Arbitrary daily max loss (e.g. INR 1 Lakh)
                return [f"Daily loss limit breached. Current PnL: {total_unrealized_pnl}"]
            return []
        except Exception as e:
            return [f"Failed to check daily loss: {e}"]"""

content = content.replace(target2, replacement2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

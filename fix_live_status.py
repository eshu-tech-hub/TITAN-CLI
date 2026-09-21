
path = 'titan/runtime/local_transport.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                    "orders": [
                        {
                            "order_id": o.broker_order_id,
                            "symbol": o.symbol,
                            "side": o.side.value if hasattr(o.side, "value") else str(o.side),
                            "type": o.order_type.value if hasattr(o.order_type, "value") else str(o.order_type),
                            "quantity": getattr(o, "quantity", getattr(o, "total_quantity", 0)),
                            "filled_quantity": getattr(o, "filled_quantity", 0),
                            "status": o.status.value if hasattr(o.status, "value") else str(o.status),
                        }
                        for o in orders
                    ]
                }"""

replacement = """                    "orders": [
                        {
                            "order_id": o.broker_order_id,
                            "symbol": o.symbol,
                            "side": o.side.value if hasattr(o.side, "value") else str(o.side),
                            "type": o.order_type.value if hasattr(o.order_type, "value") else str(o.order_type),
                            "quantity": getattr(o, "quantity", getattr(o, "total_quantity", 0)),
                            "filled_quantity": getattr(o, "filled_quantity", 0),
                            "status": o.status.value if hasattr(o.status, "value") else str(o.status),
                        }
                        for o in orders
                    ],
                    "market_status": {
                        "stream_connected": getattr(self.service.engine.stream, 'connected', getattr(self.service.engine.stream, 'is_connected', False)) if self.service.engine.stream else False,
                        "symbols": list(getattr(self.service.engine.stream, 'symbols', getattr(self.service.engine.stream, 'subscribed_symbols', []))) if self.service.engine.stream else [],
                    }
                }"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

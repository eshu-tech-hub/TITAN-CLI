
path = 'titan/brokers/yfinance/stream.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                        except Exception:
                            import traceback
                            with open("titan_crash.log", "a") as err_f:"""

replacement = """                        except Exception as e:
                            import traceback
                            with open("titan_crash.log", "a") as err_f:"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

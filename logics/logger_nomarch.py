# Декоратор логирования для немаршутизированных функций
import csv
import time


def log_time(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        start_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start))
        result = func(*args, **kwargs)
        end = time.time()
        end_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end))
        duration = round(end - start, 2)
        with open("function_logs.csv", "a", newline='', encoding='utf-8') as log_file:
            log_writer = csv.writer(log_file)
            log_writer.writerow([func.__name__, start_str, end_str, duration])
        return result
    return wrapper
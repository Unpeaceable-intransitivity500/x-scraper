from datetime import datetime, timedelta
from typing import List, Tuple


def generate_date_ranges(start_date: str, end_date: str, chunk_type: str = 'monthly') -> List[Tuple[str, str]]:
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    ranges = []
    current = start
    
    if chunk_type == 'weekly':
        while current < end:
            chunk_end = min(current + timedelta(days=7), end)
            ranges.append((
                current.strftime('%Y-%m-%d'),
                chunk_end.strftime('%Y-%m-%d')
            ))
            current = chunk_end
    
    elif chunk_type == 'monthly':
        while current < end:
            if current.month == 12:
                chunk_end = datetime(current.year + 1, 1, 1)
            else:
                chunk_end = datetime(current.year, current.month + 1, 1)
            
            chunk_end = min(chunk_end, end)
            ranges.append((
                current.strftime('%Y-%m-%d'),
                chunk_end.strftime('%Y-%m-%d')
            ))
            current = chunk_end
    
    elif chunk_type == 'quarterly':
        while current < end:
            current_quarter = (current.month - 1) // 3
            next_quarter_month = (current_quarter + 1) * 3 + 1
            
            if next_quarter_month > 12:
                chunk_end = datetime(current.year + 1, 1, 1)
            else:
                chunk_end = datetime(current.year, next_quarter_month, 1)
            
            chunk_end = min(chunk_end, end)
            ranges.append((
                current.strftime('%Y-%m-%d'),
                chunk_end.strftime('%Y-%m-%d')
            ))
            current = chunk_end
    
    return ranges


def parse_date_or_relative(date_str: str) -> str:
    if '-' in date_str:
        return date_str
    
    today = datetime.now()
    
    if 'month' in date_str.lower():
        months = int(''.join(filter(str.isdigit, date_str)))
        result_date = today - timedelta(days=months * 30)
        return result_date.strftime('%Y-%m-%d')
    
    elif 'year' in date_str.lower():
        years = int(''.join(filter(str.isdigit, date_str)))
        result_date = today - timedelta(days=years * 365)
        return result_date.strftime('%Y-%m-%d')
    
    elif 'day' in date_str.lower():
        days = int(''.join(filter(str.isdigit, date_str)))
        result_date = today - timedelta(days=days)
        return result_date.strftime('%Y-%m-%d')
    
    return date_str


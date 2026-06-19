#!/usr/bin/env python3
import os
import sys

# Add services/ to path so the shared `lib` package is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_a.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

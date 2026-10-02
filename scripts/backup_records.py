"""Consistent SQLite backup of analysis/image/review or admission DB. No credentials printed."""
import argparse,sqlite3
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('database',type=Path);parser.add_argument('backup',type=Path);args=parser.parse_args()
if not args.database.is_file():parser.error('Source database not found.')
if args.backup.exists():parser.error('Choose a new backup path; backups are never overwritten.')
source=sqlite3.connect(f'{args.database.resolve().as_uri()}?mode=ro',uri=True);destination=sqlite3.connect(args.backup)
try:source.backup(destination)
finally:destination.close();source.close()
print('SQLite backup completed. Protect this file as private survey/review data.')

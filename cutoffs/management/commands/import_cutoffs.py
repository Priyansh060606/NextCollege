import os
import pandas as pd
from django.core.management.base import BaseCommand
from colleges.models import College, Branch
from cutoffs.models import Cutoff

class Command(BaseCommand):
    help = 'Import cutoffs from CSV files (JoSAA format)'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='Path to CSV file')

    def parse_rank(self, val):
        if pd.isna(val): return 0
        val_str = str(val).strip().upper()
        # Handle Preparatory Ranks by stripping the 'P'
        if val_str.endswith('P'): 
            val_str = val_str[:-1]
        try:
            return int(val_str)
        except ValueError:
            return 0

    def handle(self, *args, **options):
        file_path = options['file']
        if not file_path or not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        self.stdout.write(f"Reading CSV file: {file_path}...")
        df = pd.read_csv(file_path)
        
        # Build cache to avoid multiple DB lookups
        colleges = {c.name: c for c in College.objects.all()}
        branches = {b.name: b for b in Branch.objects.all()}
        
        cutoffs_to_create = []
        
        for idx, row in df.iterrows():
            institute_name = str(row.get('Institute', '')).strip()
            program_name = str(row.get('Academic Program Name', '')).strip()
            
            if not institute_name or not program_name or pd.isna(row.get('Institute')):
                continue
                
            college = colleges.get(institute_name)
            if not college:
                college = College.objects.create(name=institute_name, state='Unknown')
                colleges[institute_name] = college
                
            branch = branches.get(program_name)
            if not branch:
                branch = Branch.objects.create(name=program_name)
                branches[program_name] = branch
                
            # Parse row data safely
            try:
                year = int(row.get('Year', 0))
            except ValueError:
                year = 0
            
            try:
                round_number = int(row.get('Round', 0))
            except ValueError:
                round_number = 0

            category = str(row.get('Seat Type', '')).strip()
            quota = str(row.get('Quota', '')).strip()
            seat_pool = str(row.get('Gender', '')).strip()
            
            opening_rank = self.parse_rank(row.get('Opening Rank', '0'))
            closing_rank = self.parse_rank(row.get('Closing Rank', '0'))
            
            cutoff = Cutoff(
                college=college,
                branch=branch,
                year=year,
                round_number=round_number,
                category=category,
                quota=quota,
                seat_pool=seat_pool,
                opening_rank=opening_rank,
                closing_rank=closing_rank
            )
            cutoffs_to_create.append(cutoff)
            
            if len(cutoffs_to_create) >= 5000:
                Cutoff.objects.bulk_create(cutoffs_to_create, ignore_conflicts=True)
                self.stdout.write(f"Inserted {idx + 1} records...")
                cutoffs_to_create = []

        # Insert remaining records
        if cutoffs_to_create:
            Cutoff.objects.bulk_create(cutoffs_to_create, ignore_conflicts=True)
            self.stdout.write(f"Inserted remaining {len(cutoffs_to_create)} records.")

        self.stdout.write(self.style.SUCCESS(f"Successfully imported {file_path}"))

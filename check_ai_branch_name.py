import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NextCollege.settings')
django.setup()

from colleges.models import Branch
branches = Branch.objects.filter(name__icontains='Computer Science').filter(name__icontains='Artificial Intelligence')
print(f"Total branches matching: {branches.count()}")
for b in branches:
    print(f" - {b.name}")

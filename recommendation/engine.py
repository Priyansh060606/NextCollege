from cutoffs.models import Cutoff
from colleges.models import College, Branch
from django.db.models import Max

class RecommendationEngine:
    def __init__(self):
        pass

    def _calculate_probability(self, closing_rank, student_rank):
        """
        Calculate admission probability based on the ratio of closing_rank to student_rank.
        Matches the logic in ResultView for consistency.
        """
        ratio = closing_rank / max(student_rank, 1)
        
        if ratio >= 5.0:
            prob = 98
        elif ratio >= 3.0:
            prob = 92 + (ratio - 3.0) / 2.0 * 6
        elif ratio >= 2.0:
            prob = 85 + (ratio - 2.0) / 1.0 * 7
        elif ratio >= 1.5:
            prob = 75 + (ratio - 1.5) / 0.5 * 10
        elif ratio >= 1.2:
            prob = 60 + (ratio - 1.2) / 0.3 * 15
        elif ratio >= 1.0:
            prob = 40 + (ratio - 1.0) / 0.2 * 20
        elif ratio >= 0.8:
            prob = 20 + (ratio - 0.8) / 0.2 * 20
        elif ratio >= 0.5:
            prob = 8 + (ratio - 0.5) / 0.3 * 12
        else:
            prob = max(3, 3 + ratio / 0.5 * 5)
        
        return int(round(min(98, max(3, prob)), 0))

    def _generate_action_plan(self, rank, category, seat_pool, state):
        plan = []
        
        # Round 1 Analysis
        r1_desc = f"As a {category} candidate with rank {rank}, "
        if rank < 5000:
            r1_desc += "you are in a highly competitive top-tier bracket. You are likely to get a premium allotment in Round 1. Only 'Freeze' if you get a top 5 IIT/NIT, otherwise firmly choose 'Float'."
        elif rank < 25000:
            r1_desc += "you have solid chances in mid-tier NITs and IIITs. Do not panic if Round 1 doesn't yield your dream branch. Always 'Float' to stay eligible for upgrades."
        else:
            r1_desc += "your strategy relies heavily on later rounds"
            if state:
                r1_desc += f" and utilizing your {state} Home State quota to its maximum potential."
            else:
                r1_desc += " and specialized quotas."
            r1_desc += " Expect initial allotments to be lower-tier; patience is key."
            
        plan.append({'title': "Round 1: Initial Positioning", 'description': r1_desc})
        
        # Round 2 Dynamics
        r2_desc = "Cutoffs usually shift by 2-5% here. "
        if category != 'OPEN':
            r2_desc += f"Since you are in the {category} category, category-specific seat matrices often cause sudden, volatile drops in closing ranks. Stay patient."
        elif seat_pool == 'Female-Only':
            r2_desc += "Supernumerary seats for female candidates often see significant unpredictable movement. Keep floating your options."
        else:
            r2_desc += "Monitor your floated seat. If you've been upgraded to a preferred institute but want a better branch within it, switch to 'Slide'."
            
        plan.append({'title': "Round 2: Trend Observation", 'description': r2_desc})

        # Round 3 Dynamics
        r3_desc = "This round often filters out candidates who forgot to pay seat acceptance fees or failed document verification. "
        if rank < 15000:
            r3_desc += "You might see a slight upgrade into a better NIT or a more preferred branch like ECE or IT."
        else:
            r3_desc += "Keep your expectations grounded but remain in the 'Float' status unless you've hit your absolute top preference."
        
        plan.append({'title': "Round 3: The Mid-Point Squeeze", 'description': r3_desc})
        
        # Round 4 Strategy
        r4_desc = "Historically, Round 4 is the 'Vacuum Round'. Many students withdraw their seats here to avoid fee forfeiture. "
        if rank > 25000:
            r4_desc += "This is precisely where candidates in your rank bracket see the most dramatic jumps. Your 'Target' colleges will likely solidify here."
        else:
            r4_desc += "You might see an unexpected jump into your 'Dream' bracket as upper seats clear out."
            
        plan.append({'title': "Round 4: The Major Shift", 'description': r4_desc})
        
        # Round 5 & CSAB Strategy
        r5_desc = "Evaluate your final JoSAA allotment carefully. "
        if rank > 35000:
            r5_desc += "Given your rank, do NOT settle if you are unhappy with the branch. Prepare heavily for the CSAB Special Rounds where thousands of vacant seats in NITs/IIITs/GFTIs are filled."
        else:
            r5_desc += "If you secured your Target or Dream college, congratulations! CSAB is generally not necessary unless you missed your top preference by a tiny margin."
            
        plan.append({'title': "Round 5: Final Decisions & CSAB", 'description': r5_desc})
        
        return plan

    def generate_strategy(self, student_rank, category, seat_pool, state=None, branch=None):
        # 1. Get the latest year in the database
        latest_year = Cutoff.objects.aggregate(Max('year'))['year__max'] or 2025

        # 2. Heuristic Filter: Find realistic options from the latest year
        min_rank_threshold = max(1, int(student_rank * 0.3))
        max_rank_threshold = int(student_rank * 3.0)

        from django.db.models import Q
        
        query = Q(
            year=latest_year,
            category=category,
            seat_pool=seat_pool,
            closing_rank__gte=min_rank_threshold,
            closing_rank__lte=max_rank_threshold
        )
        
        if state:
            query &= (Q(quota__in=['AI', 'OS']) | Q(quota='HS', college__state__iexact=state))
        else:
            query &= Q(quota__in=['AI', 'OS'])

        if branch:
            b_clean = branch.strip()
            b_query = Q(branch__name__icontains=b_clean)
            if b_clean.upper() in ['CSE', 'CS']:
                b_query |= Q(branch__name__icontains='Computer') | Q(branch__name__icontains='Computing')
            elif b_clean.upper() in ['ECE', 'EC']:
                b_query |= Q(branch__name__icontains='Electronics') | Q(branch__name__icontains='Communication')
            elif b_clean.upper() in ['IT']:
                b_query |= Q(branch__name__icontains='Information')
            elif b_clean.upper() in ['AI', 'DS']:
                b_query |= Q(branch__name__icontains='Artificial') | Q(branch__name__icontains='Data')
            
            branch_filtered_query = query & b_query
            candidates = Cutoff.objects.filter(branch_filtered_query).select_related('college', 'branch')
            if not candidates.exists():
                candidates = Cutoff.objects.filter(query).select_related('college', 'branch')
        else:
            candidates = Cutoff.objects.filter(query).select_related('college', 'branch')

        # Deduplicate candidates (take the last round's cutoff for each college-branch combo)
        unique_candidates = {}
        for c in candidates:
            key = (c.college_id, c.branch_id)
            if key not in unique_candidates or c.round_number > unique_candidates[key].round_number:
                unique_candidates[key] = c

        if not unique_candidates:
            return {"dream": [], "target": [], "safe": []}

        # 3. Calculate probabilities using ratio-based heuristic
        candidate_list = list(unique_candidates.values())

        # 4. Categorize into Dream, Target, Safe
        dream, target, safe = [], [], []

        for cand in candidate_list:
            prob = self._calculate_probability(cand.closing_rank, student_rank)

            result = {
                'college': cand.college.name,
                'branch': cand.branch.name,
                'historical_closing_rank': cand.closing_rank,
                'admission_probability': prob
            }
            
            if prob >= 75:
                safe.append(result)
            elif prob >= 40:
                target.append(result)
            else:
                dream.append(result)
                
        # Sort each list by probability descending
        dream.sort(key=lambda x: x['admission_probability'], reverse=True)
        target.sort(key=lambda x: x['admission_probability'], reverse=True)
        safe.sort(key=lambda x: x['admission_probability'], reverse=True)

        # 5. Build Dynamic Choice Filling Order (Optimal sequence)
        choice_order = []
        # Combine safe, target, dream for optimal sequence
        top_candidates = safe[:3] + target[:3] + dream[:2]
        top_candidates.sort(key=lambda x: x['admission_probability'], reverse=True)
        
        icons = ['verified', 'trending_up', 'check_circle', 'star', 'workspace_premium']
        for i, c in enumerate(top_candidates[:5]):
            prob = c['admission_probability']
            if prob >= 80:
                reason = "High Admission Probability (Safe Bet)"
            elif prob >= 60:
                reason = "Balanced Option (Target Rank)"
            elif prob >= 40:
                reason = "Top Tier Opportunity (Moderate Chance)"
            else:
                reason = "Dream Reach (Aim High)"

            choice_order.append({
                'rank_num': i + 1,
                'college': c['college'],
                'branch': c['branch'],
                'closing_rank': c['historical_closing_rank'],
                'match': prob,
                'reason': reason,
                'icon': icons[i % len(icons)]
            })

        # 6. Build Dynamic College Comparison (Top 4 unique colleges)
        comparison_colleges = []
        seen_colleges = set()
        for cand in candidate_list:
            col = cand.college
            if col.id not in seen_colleges:
                seen_colleges.add(col.id)
                roi_str = "N/A"
                if col.average_fees and col.average_fees > 0 and col.average_package:
                    roi_val = (float(col.average_package) * 100000) / float(col.average_fees)
                    roi_str = f"{round(roi_val, 1)}x"

                comparison_colleges.append({
                    'name': col.short_name or col.name[:18],
                    'full_name': col.name,
                    'avg_package': f"₹{col.average_package} LPA" if col.average_package else "N/A",
                    'fees': f"₹{col.average_fees_lakhs}L" if col.average_fees_lakhs else "N/A",
                    'nirf': f"#{col.nirf_rank}" if col.nirf_rank else "N/A",
                    'roi': roi_str,
                    'closing_rank': f"{cand.closing_rank:,}"
                })
            if len(comparison_colleges) >= 4:
                break

        # 7. Build Dynamic Trend Chart Data for Top College/Branch
        trend_years = ['2021', '2022', '2023', '2024', '2025']
        trend_ranks = [int(student_rank * 0.9), int(student_rank * 0.93), int(student_rank * 0.95), int(student_rank * 0.97), student_rank]
        trend_title = "Closing Rank Trend"

        if candidate_list:
            top_cand = candidate_list[0]
            trend_title = f"{top_cand.college.name} — {top_cand.branch.name}"
            from django.db.models import Avg
            yearly_cutoffs = Cutoff.objects.filter(
                college=top_cand.college,
                branch=top_cand.branch,
                category=category,
                seat_pool=seat_pool
            ).values('year').annotate(cr=Avg('closing_rank')).order_by('year')

            if len(yearly_cutoffs) >= 2:
                trend_years = [str(y['year']) for y in yearly_cutoffs]
                trend_ranks = [int(round(y['cr'])) for y in yearly_cutoffs]

        return {
            "dream": dream[:15],
            "target": target[:15],
            "safe": safe[:15],
            "choice_order": choice_order,
            "comparison_colleges": comparison_colleges,
            "trend_years": trend_years,
            "trend_ranks": trend_ranks,
            "trend_title": trend_title,
            "action_plan": self._generate_action_plan(student_rank, category, seat_pool, state)
        }


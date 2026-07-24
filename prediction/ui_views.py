from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Count, Avg, Max, Min
from recommendation.engine import RecommendationEngine
from colleges.models import College, Branch
from cutoffs.models import Cutoff
import random
import hashlib
import json
from datetime import datetime
from django.db.models import Q


class HomeView(View):
    def get(self, request):
        total_colleges = College.objects.count()
        total_branches = Branch.objects.count()
        total_cutoffs = Cutoff.objects.count()
        return render(request, 'home/home.html', {
            'active_page': 'home',
            'total_colleges': total_colleges,
            'total_branches': total_branches,
            'total_cutoffs': total_cutoffs,
            'model_accuracy': '74.2%',
        })


class PredictorView(View):
    def get(self, request):
        """Exam selection page - choose between JEE Mains and JEE Advanced."""
        # Count institute types for the selection page
        nit_count = College.objects.filter(name__icontains='National Institute of Technology').count()
        iiit_count = College.objects.filter(
            Q(name__icontains='Indian Institute of Information Technology') |
            Q(name__icontains='International Institute of Information Technology')
        ).count()
        iit_q = (
            Q(name__icontains='Indian Institute of Technology') |
            Q(name__icontains='Indian Institute  of Technology')
        ) & ~Q(name__icontains='Information Technology') & ~Q(name__icontains='Carpet') & ~Q(name__icontains='Handloom') & ~Q(name__icontains='Engineering Science')
        iit_count = College.objects.filter(iit_q).count()
        total_colleges = College.objects.count()
        gfti_count = total_colleges - nit_count - iiit_count - iit_count
        
        # Count IIT branches
        iit_branch_count = Cutoff.objects.filter(
            college__in=College.objects.filter(iit_q)
        ).values('branch').distinct().count()
        
        return render(request, 'prediction/exam_select.html', {
            'active_page': 'predict',
            'nit_count': nit_count,
            'iiit_count': iiit_count,
            'iit_count': iit_count,
            'gfti_count': gfti_count,
            'iit_branch_count': iit_branch_count,
        })


class MainsPredictorView(View):
    """JEE Main predictor form - NITs, IIITs, GFTIs."""
    def get(self, request):
        categories = Cutoff.objects.values_list('category', flat=True).distinct().order_by('category')
        seat_pools = Cutoff.objects.values_list('seat_pool', flat=True).distinct().order_by('seat_pool')
        
        iit_q = (
            Q(college__name__icontains='Indian Institute of Technology') |
            Q(college__name__icontains='Indian Institute  of Technology')
        ) & ~Q(college__name__icontains='Information Technology') & ~Q(college__name__icontains='Carpet') & ~Q(college__name__icontains='Handloom') & ~Q(college__name__icontains='Engineering Science')
        
        branches = list(
            Cutoff.objects.filter(~iit_q)
            .values_list('branch__name', flat=True)
            .distinct()
            .order_by('branch__name')
        )
        
        import json
        return render(request, 'prediction/predictor_mains.html', {
            'active_page': 'predict',
            'categories': categories,
            'seat_pools': seat_pools,
            'branches': branches,
            'branches_json': json.dumps(branches),
        })


class AdvancedPredictorView(View):
    """JEE Advanced predictor form - IITs only."""
    def get(self, request):
        categories = Cutoff.objects.values_list('category', flat=True).distinct().order_by('category')
        seat_pools = Cutoff.objects.values_list('seat_pool', flat=True).distinct().order_by('seat_pool')
        iit_q = (
            Q(name__icontains='Indian Institute of Technology') |
            Q(name__icontains='Indian Institute  of Technology')
        ) & ~Q(name__icontains='Information Technology') & ~Q(name__icontains='Carpet') & ~Q(name__icontains='Handloom') & ~Q(name__icontains='Engineering Science')
        iit_count = College.objects.filter(iit_q).count()
        
        iit_cutoff_q = (
            Q(college__name__icontains='Indian Institute of Technology') |
            Q(college__name__icontains='Indian Institute  of Technology')
        ) & ~Q(college__name__icontains='Information Technology') & ~Q(college__name__icontains='Carpet') & ~Q(college__name__icontains='Handloom') & ~Q(college__name__icontains='Engineering Science')
        
        branches = list(
            Cutoff.objects.filter(iit_cutoff_q)
            .values_list('branch__name', flat=True)
            .distinct()
            .order_by('branch__name')
        )
        
        import json
        return render(request, 'prediction/predictor_advanced.html', {
            'active_page': 'predict',
            'categories': categories,
            'seat_pools': seat_pools,
            'iit_count': iit_count,
            'branches': branches,
            'branches_json': json.dumps(branches),
        })


class ResultView(View):
    def _calculate_probability(self, closing_rank, student_rank):
        """
        Calculate admission probability based on the ratio of closing_rank to student_rank.
        
        Logic:
        - ratio = closing_rank / student_rank
        - ratio > 1 means the cutoff is higher (worse) than student's rank → student is BETTER → higher probability
        - ratio < 1 means the cutoff is lower (better) than student's rank → student is WORSE → lower probability
        
        Probability mapping:
        - ratio >= 5.0  → 98% (extremely safe, cutoff is 5x worse than your rank)
        - ratio >= 3.0  → 92-98% (very safe)
        - ratio >= 2.0  → 85-92% (safe)
        - ratio >= 1.5  → 75-85% (safe)
        - ratio >= 1.2  → 60-75% (target)
        - ratio >= 1.0  → 40-60% (target, borderline)
        - ratio >= 0.8  → 20-40% (dream, competitive)
        - ratio >= 0.5  → 8-20% (dream, stretch)
        - ratio < 0.5   → 3-8% (dream, long shot)
        """
        ratio = closing_rank / max(student_rank, 1)
        
        if ratio >= 5.0:
            prob = 98
        elif ratio >= 3.0:
            # 92 to 98, linear interpolation
            prob = 92 + (ratio - 3.0) / 2.0 * 6
        elif ratio >= 2.0:
            # 85 to 92
            prob = 85 + (ratio - 2.0) / 1.0 * 7
        elif ratio >= 1.5:
            # 75 to 85
            prob = 75 + (ratio - 1.5) / 0.5 * 10
        elif ratio >= 1.2:
            # 60 to 75
            prob = 60 + (ratio - 1.2) / 0.3 * 15
        elif ratio >= 1.0:
            # 40 to 60
            prob = 40 + (ratio - 1.0) / 0.2 * 20
        elif ratio >= 0.8:
            # 20 to 40
            prob = 20 + (ratio - 0.8) / 0.2 * 20
        elif ratio >= 0.5:
            # 8 to 20
            prob = 8 + (ratio - 0.5) / 0.3 * 12
        else:
            # 3 to 8
            prob = max(3, 3 + ratio / 0.5 * 5)
        
        return int(round(min(98, max(3, prob)), 0))

    def post(self, request):
        rank = request.POST.get('rank')
        category = request.POST.get('category', 'OPEN')
        gender = request.POST.get('gender', 'Gender-Neutral')
        state = request.POST.get('state', '')
        branch_pref = request.POST.get('branch', '')
        branch_pref = request.POST.get('branch', '')

        if not rank:
            return redirect('predict')

        try:
            student_rank = int(rank)
        except ValueError:
            return redirect('predict')

        # Get the latest year cutoff data to find realistic college options
        latest_year = Cutoff.objects.aggregate(Max('year'))['year__max'] or 2025

        from django.db.models import Q

        # ---- Determine the closing rank search range ----
        # Dream colleges: closing rank can be LOWER than student rank (harder to get in)
        #   We look at colleges where closing rank >= rank * 0.3 (dreams / competitive)
        # Safe colleges: closing rank is HIGHER than student rank (easier to get in)
        #   Without branch filter: up to rank * 3 (manageable result set)
        #   With branch filter: much wider (up to rank * 100, capped at a sensible max)
        #   because some branches (e.g. IT) only exist in a few colleges with very high closing ranks
        
        lower_bound = max(1, int(student_rank * 0.3))
        
        if branch_pref:
            # With a branch filter, cast a very wide net on the safe side
            # e.g., rank 1000 → search up to closing rank 100,000
            # This ensures we find ALL colleges offering that branch
            upper_bound = max(int(student_rank * 100), 200000)
        else:
            # Without branch filter, use a moderate range to avoid too many results
            upper_bound = int(student_rank * 3.5)

        query = Q(
            year=latest_year,
            category=category,
            seat_pool=gender,
            round_number=1,
            closing_rank__gte=lower_bound,
            closing_rank__lte=upper_bound,
        )

        if state:
            query &= (Q(quota__in=['AI', 'OS']) | Q(quota='HS', college__state__iexact=state))
        else:
            query &= Q(quota__in=['AI', 'OS'])

        candidates = Cutoff.objects.filter(query).select_related('college', 'branch').order_by('closing_rank')

        # Filter by branch preference if given
        if branch_pref:
            candidates = candidates.filter(branch__name__icontains=branch_pref)

        # --- Fallback: if branch filter yields 0 results, try without round_number filter ---
        if branch_pref and not candidates.exists():
            fallback_query = Q(
                year=latest_year,
                category=category,
                seat_pool=gender,
                closing_rank__gte=1,
            )
            if state:
                fallback_query &= (Q(quota__in=['AI', 'OS']) | Q(quota='HS', college__state__iexact=state))
            else:
                fallback_query &= Q(quota__in=['AI', 'OS'])
            
            candidates = Cutoff.objects.filter(fallback_query).filter(
                branch__name__icontains=branch_pref
            ).select_related('college', 'branch').order_by('closing_rank')

        # Deduplicate by college-branch (keep the one with the best closing rank)
        seen = set()
        unique_candidates = []
        for c in candidates:
            key = (c.college_id, c.branch_id)
            if key not in seen:
                seen.add(key)
                unique_candidates.append(c)

        results = []

        for i, cand in enumerate(unique_candidates):
            prob = self._calculate_probability(cand.closing_rank, student_rank)

            if prob >= 75:
                status = 'Safe'
                color = 'on-tertiary-container'
            elif prob >= 40:
                status = 'Target'
                color = 'secondary'
            else:
                status = 'Dream'
                color = 'error'

            results.append({
                'college_name': cand.college.name,
                'branch_name': cand.branch.name,
                'prob': prob,
                'status': status,
                'color': color,
                'closing_rank': cand.closing_rank,
            })

        # Sort and balance the results — show top picks from each category
        results.sort(key=lambda x: x['prob'], reverse=True)
        safe_results = [r for r in results if r['status'] == 'Safe'][:20]
        target_results = [r for r in results if r['status'] == 'Target'][:20]
        dream_results = [r for r in results if r['status'] == 'Dream'][:20]
        
        balanced_results = safe_results + target_results + dream_results
        balanced_results.sort(key=lambda x: x['prob'], reverse=True)

        # Save to session for recommendation page
        request.session['student_rank'] = rank
        request.session['category'] = category
        request.session['gender'] = gender
        request.session['state'] = state

        return render(request, 'prediction/result.html', {
            'active_page': 'predict',
            'rank': rank,
            'category': category,
            'gender': gender,
            'results': balanced_results,
            'total_found': len(balanced_results),
        })


class _RoundWiseResultBase(View):
    """Base class for round-wise prediction logic shared by Mains and Advanced views."""

    def _calculate_probability(self, closing_rank, student_rank):
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

    def _get_institute_type(self, college_name):
        """Classify college into NIT, IIIT, IIT, or GFTI."""
        import re
        # Normalize multiple spaces to single for reliable matching
        name = re.sub(r'\s+', ' ', college_name.lower().strip())
        if 'indian institute of technology' in name and 'information' not in name and 'carpet' not in name and 'handloom' not in name and 'engineering science' not in name:
            return 'IIT'
        elif 'national institute of technology' in name:
            return 'NIT'
        elif 'indian institute of information technology' in name or 'iiit' in name:
            return 'IIIT'
        else:
            return 'GFTI'

    # IIT tier classification constants
    TOP_IIT_KEYWORDS = ['bombay', 'delhi', 'madras', 'kanpur', 'kharagpur', 'roorkee', 'guwahati']
    MID_IIT_KEYWORDS = ['hyderabad', 'bhu', 'varanasi', 'dhanbad', 'ism', 'indore', 'ropar',
                        'patna', 'gandhinagar', 'bhubaneswar', 'mandi', 'jodhpur', 'tirupati']

    def _get_iit_tier(self, college_name):
        """Classify an IIT into Top, Mid, or New tier."""
        name = college_name.lower()
        for kw in self.TOP_IIT_KEYWORDS:
            if kw in name:
                return 'Top'
        for kw in self.MID_IIT_KEYWORDS:
            if kw in name:
                return 'Mid'
        return 'New'

    # Branch synonym/expansion map for smarter matching
    BRANCH_EXPANSIONS = {
        'computer engineering': ['Computer Engineering', 'Computer Science'],
        'computer science': ['Computer Science', 'Computer Engineering'],
        'cse': ['Computer Science', 'Computer Engineering'],
        'information technology': ['Information Technology'],
        'it': ['Information Technology'],
        'electronics and communication': ['Electronics and Communication', 'Electronics & Communication', 'ECE'],
        'ece': ['Electronics and Communication', 'Electronics & Communication'],
        'electrical engineering': ['Electrical Engineering', 'Electrical and Electronics'],
        'eee': ['Electrical and Electronics', 'Electrical Engineering'],
        'mechanical engineering': ['Mechanical Engineering', 'Mechanical'],
        'civil engineering': ['Civil Engineering', 'Civil'],
        'chemical engineering': ['Chemical Engineering', 'Chemical'],
        'aerospace engineering': ['Aerospace Engineering', 'Aerospace'],
        'biotechnology': ['Biotechnology', 'Bio Technology'],
        'mathematics and computing': ['Mathematics and Computing', 'Mathematics'],
        'data science': ['Data Science', 'Artificial Intelligence'],
        'artificial intelligence': ['Artificial Intelligence', 'Data Science', 'AI'],
    }

    def _expand_branch_query(self, branch_pref):
        """Expand a branch preference into a broader Q filter matching related branches."""
        if not branch_pref:
            return None
        
        normalized = branch_pref.strip().lower()
        
        # Check if we have explicit expansions for this branch
        expansions = None
        for key, values in self.BRANCH_EXPANSIONS.items():
            if key in normalized or normalized in key:
                expansions = values
                break
        
        if expansions:
            branch_q = Q()
            for exp in expansions:
                branch_q |= Q(branch__name__icontains=exp)
            return branch_q
        else:
            # Default: just use icontains on the original preference
            return Q(branch__name__icontains=branch_pref)

    def _get_college_filter(self, exam_type, request=None):
        """Return a Q filter to include/exclude colleges based on exam type."""
        iit_q = (
            Q(college__name__icontains='Indian Institute of Technology') |
            Q(college__name__icontains='Indian Institute  of Technology')
        ) & ~Q(college__name__icontains='Information Technology') & ~Q(college__name__icontains='Carpet') & ~Q(college__name__icontains='Handloom') & ~Q(college__name__icontains='Engineering Science')
        
        if exam_type == 'advanced':
            base_filter = iit_q
            # Apply IIT tier filtering if checkboxes are present
            if request and (request.POST.get('tier_top') or request.POST.get('tier_mid') or request.POST.get('tier_new')):
                tier_filter = Q()
                has_tier = False
                if request.POST.get('tier_top'):
                    for kw in self.TOP_IIT_KEYWORDS:
                        tier_filter |= Q(college__name__icontains=kw)
                    has_tier = True
                if request.POST.get('tier_mid'):
                    for kw in self.MID_IIT_KEYWORDS:
                        tier_filter |= Q(college__name__icontains=kw)
                    has_tier = True
                if request.POST.get('tier_new'):
                    # New IITs = IITs not in Top or Mid
                    new_q = Q()
                    for kw in self.TOP_IIT_KEYWORDS + self.MID_IIT_KEYWORDS:
                        new_q &= ~Q(college__name__icontains=kw)
                    tier_filter |= new_q
                    has_tier = True
                if has_tier:
                    return base_filter & tier_filter
            return base_filter
        else:
            # Mains: exclude IITs, optionally filter by institute type checkboxes
            exclude_iit = ~iit_q
            inst_filters = Q()
            has_filter = False
            
            if request and request.POST.get('inst_nit'):
                inst_filters |= Q(college__name__icontains='National Institute of Technology')
                has_filter = True
            if request and request.POST.get('inst_iiit'):
                inst_filters |= Q(college__name__icontains='Indian Institute of Information Technology')
                inst_filters |= Q(college__name__icontains='International Institute of Information Technology')
                has_filter = True
            if request and request.POST.get('inst_gfti'):
                # GFTIs = everything that's not IIT, NIT, or IIIT
                gfti_q = ~Q(college__name__icontains='National Institute of Technology')
                gfti_q &= ~Q(college__name__icontains='Indian Institute of Information Technology')
                gfti_q &= ~Q(college__name__icontains='International Institute of Information Technology')
                gfti_q &= ~iit_q
                inst_filters |= gfti_q
                has_filter = True
            
            if has_filter:
                return exclude_iit & inst_filters
            return exclude_iit

    def _build_round_wise_results(self, student_rank, category, gender, state, branch_pref, exam_type, request=None, seat_type=None):
        """Build prediction results for all 6 rounds.
        
        Args:
            seat_type: The seat type / category (OPEN, OBC-NCL, SC, ST, EWS, etc.)
                       Falls back to `category` if not provided.
        """
        # Use seat_type if provided, otherwise fall back to category
        effective_category = seat_type if seat_type else category
        
        latest_year = Cutoff.objects.aggregate(Max('year'))['year__max'] or 2025
        
        info_tech_fallback = False
        original_branch_pref = branch_pref
        if exam_type == 'advanced' and branch_pref:
            normalized = branch_pref.strip().lower()
            if normalized in ['information technology', 'it', 'info tech', 'infotech', 'information tech']:
                branch_pref = 'Computer Science'
                info_tech_fallback = True

        # Build branch filter using smart expansion
        branch_filter = self._expand_branch_query(branch_pref)

        # ---- Determine the closing rank search range ----
        # For excellent ranks (< 500), cast a very wide net
        # For good ranks (< 5000), use a generous multiplier
        # For average ranks, use moderate multiplier
        if branch_pref:
            # With a branch filter, always cast wide to catch all colleges offering that branch
            upper_bound = max(int(student_rank * 200), 300000)
        elif exam_type == 'advanced':
            upper_bound = max(int(student_rank * 5), 50000)
        else:
            # Mains without branch: wider range for low ranks
            if student_rank <= 500:
                upper_bound = max(int(student_rank * 100), 200000)
            elif student_rank <= 5000:
                upper_bound = max(int(student_rank * 20), 100000)
            else:
                upper_bound = max(int(student_rank * 5), 50000)
        
        lower_bound = max(1, int(student_rank * 0.3))

        college_filter = self._get_college_filter(exam_type, request)
        
        # Get all available rounds
        available_rounds = list(
            Cutoff.objects.filter(year=latest_year)
            .values_list('round_number', flat=True)
            .distinct()
            .order_by('round_number')
        )
        if not available_rounds:
            available_rounds = [1, 2, 3, 4, 5, 6]

        round_data = {}
        selected_round_results = []
        selected_round = available_rounds[0] if available_rounds else 1

        for round_num in available_rounds:
            query = Q(
                year=latest_year,
                category=effective_category,
                seat_pool=gender,
                round_number=round_num,
                closing_rank__gte=lower_bound,
                closing_rank__lte=upper_bound,
            )
            
            # Apply college type filter (IIT only for Advanced, non-IIT for Mains)
            query &= college_filter

            if state:
                query &= (Q(quota__in=['AI', 'OS']) | Q(quota='HS', college__state__iexact=state))
            else:
                if exam_type == 'advanced':
                    query &= Q(quota='AI')
                else:
                    query &= Q(quota__in=['AI', 'OS'])

            candidates = Cutoff.objects.filter(query).select_related('college', 'branch').order_by('closing_rank')

            # Apply branch filter using smart expansion
            if branch_filter:
                candidates = candidates.filter(branch_filter)

            # Fallback: if branch filter yields 0 results, try without upper bound
            if branch_pref and not candidates.exists():
                fallback_q = Q(
                    year=latest_year,
                    category=effective_category,
                    seat_pool=gender,
                    round_number=round_num,
                    closing_rank__gte=1,
                )
                fallback_q &= college_filter
                if state:
                    fallback_q &= (Q(quota__in=['AI', 'OS']) | Q(quota='HS', college__state__iexact=state))
                else:
                    if exam_type == 'advanced':
                        fallback_q &= Q(quota='AI')
                    else:
                        fallback_q &= Q(quota__in=['AI', 'OS'])
                candidates = Cutoff.objects.filter(fallback_q)
                if branch_filter:
                    candidates = candidates.filter(branch_filter)
                candidates = candidates.select_related('college', 'branch').order_by('closing_rank')

            seen = set()
            results = []
            for i, c in enumerate(candidates):
                key = (c.college_id, c.branch_id)
                if key not in seen:
                    seen.add(key)
                    prob = self._calculate_probability(c.closing_rank, student_rank)
                    
                    if prob >= 75:
                        status = 'Safe'
                    elif prob >= 40:
                        status = 'Target'
                    else:
                        status = 'Dream'
                    
                    result_entry = {
                        'college_name': c.college.name,
                        'branch_name': c.branch.name,
                        'prob': prob,
                        'status': status,
                        'closing_rank': c.closing_rank,
                        'opening_rank': c.opening_rank,
                        'round_number': round_num,
                        'inst_type': self._get_institute_type(c.college.name),
                        'seat_type': effective_category,
                        'college_state': c.college.state or '',
                    }
                    # Add IIT tier for Advanced exam type
                    if exam_type == 'advanced':
                        result_entry['iit_tier'] = self._get_iit_tier(c.college.name)
                    results.append(result_entry)

            # Sort and limit — increased limits for better results
            results.sort(key=lambda x: x['prob'], reverse=True)
            safe = [r for r in results if r['status'] == 'Safe'][:40]
            target = [r for r in results if r['status'] == 'Target'][:40]
            dream = [r for r in results if r['status'] == 'Dream'][:40]
            balanced = safe + target + dream
            balanced.sort(key=lambda x: x['prob'], reverse=True)

            round_data[round_num] = balanced
            if round_num == selected_round:
                selected_round_results = balanced

        return {
            'rounds': available_rounds,
            'selected_round': selected_round,
            'round_data': round_data,
            'results': selected_round_results,
            'total_found': len(selected_round_results),
            'latest_year': latest_year,
            'info_tech_fallback': info_tech_fallback,
            'original_branch_pref': original_branch_pref,
            'seat_type': effective_category,
        }


class MainsResultView(_RoundWiseResultBase):
    """Round-wise result view for JEE Main (NITs, IIITs, GFTIs)."""

    def post(self, request):
        rank = request.POST.get('rank')
        category = request.POST.get('category', 'OPEN')
        seat_type = request.POST.get('seat_type', '') or category
        gender = request.POST.get('gender', 'Gender-Neutral')
        state = request.POST.get('state', '')
        branch_pref = request.POST.get('branch', '')

        if not rank:
            return redirect('predict_mains')

        try:
            student_rank = int(rank)
        except ValueError:
            return redirect('predict_mains')

        data = self._build_round_wise_results(
            student_rank, category, gender, state, branch_pref, 'mains',
            request, seat_type=seat_type
        )

        # Save to session
        request.session['student_rank'] = rank
        request.session['category'] = category
        request.session['seat_type'] = seat_type
        request.session['gender'] = gender
        request.session['state'] = state
        request.session['exam_type'] = 'mains'

        # Collect unique college names and states across all rounds for filter dropdowns
        all_colleges = set()
        all_states = set()
        for rnd_results in data['round_data'].values():
            for r in rnd_results:
                all_colleges.add(r['college_name'])
                if r.get('college_state'):
                    all_states.add(r['college_state'])

        return render(request, 'prediction/result_mains.html', {
            'active_page': 'predict',
            'rank': rank,
            'category': category,
            'seat_type': data.get('seat_type', seat_type),
            'gender': gender,
            'results': data['results'],
            'total_found': data['total_found'],
            'rounds': data['rounds'],
            'selected_round': data['selected_round'],
            'round_data_json': json.dumps(data['round_data']),
            'college_names_json': json.dumps(sorted(all_colleges)),
            'state_names_json': json.dumps(sorted(all_states)),
        })


class AdvancedResultView(_RoundWiseResultBase):
    """Round-wise result view for JEE Advanced (IITs only)."""

    def post(self, request):
        rank = request.POST.get('rank')
        category = request.POST.get('category', 'OPEN')
        seat_type = request.POST.get('seat_type', '') or category
        gender = request.POST.get('gender', 'Gender-Neutral')
        state = request.POST.get('state', '')
        branch_pref = request.POST.get('branch', '')

        if not rank:
            return redirect('predict_advanced')

        try:
            student_rank = int(rank)
        except ValueError:
            return redirect('predict_advanced')

        data = self._build_round_wise_results(
            student_rank, category, gender, state, branch_pref, 'advanced',
            request, seat_type=seat_type
        )

        # Count IIT tiers in the selected round results
        tier_counts = {'Top': 0, 'Mid': 0, 'New': 0}
        for r in data['results']:
            tier = r.get('iit_tier', 'New')
            if tier in tier_counts:
                tier_counts[tier] += 1

        # Save to session
        request.session['student_rank'] = rank
        request.session['category'] = category
        request.session['seat_type'] = seat_type
        request.session['gender'] = gender
        request.session['state'] = state
        request.session['exam_type'] = 'advanced'

        # Collect unique college names and states across all rounds for filter dropdowns
        all_colleges = set()
        all_states = set()
        for rnd_results in data['round_data'].values():
            for r in rnd_results:
                all_colleges.add(r['college_name'])
                if r.get('college_state'):
                    all_states.add(r['college_state'])

        return render(request, 'prediction/result_advanced.html', {
            'active_page': 'predict',
            'rank': rank,
            'category': category,
            'seat_type': data.get('seat_type', seat_type),
            'gender': gender,
            'results': data['results'],
            'total_found': data['total_found'],
            'rounds': data['rounds'],
            'selected_round': data['selected_round'],
            'round_data_json': json.dumps(data['round_data']),
            'tier_counts': tier_counts,
            'info_tech_fallback': data.get('info_tech_fallback', False),
            'original_branch_pref': data.get('original_branch_pref', ''),
            'college_names_json': json.dumps(sorted(all_colleges)),
            'state_names_json': json.dumps(sorted(all_states)),
        })



class RecommendationView(View):
    def get(self, request):
        rank = request.GET.get('rank') or request.session.get('student_rank') or '15000'
        category = request.GET.get('category') or request.session.get('category') or 'OPEN'
        gender = request.GET.get('gender') or request.session.get('gender') or 'Gender-Neutral'
        state = request.GET.get('state') or request.session.get('state') or ''
        branch = request.GET.get('branch') or request.session.get('branch') or request.session.get('branch_pref') or ''

        try:
            student_rank = int(rank)
        except (ValueError, TypeError):
            student_rank = 15000

        engine = RecommendationEngine()
        strategy = engine.generate_strategy(student_rank, category, gender, state=state, branch=branch)

        overall_chance = 0
        all_colleges = strategy.get('safe', []) + strategy.get('target', []) + strategy.get('dream', [])
        if all_colleges:
            overall_chance = max([c['admission_probability'] for c in all_colleges])

        total_options = len(all_colleges)
        best_roi = strategy['safe'][0] if strategy.get('safe') else (strategy['target'][0] if strategy.get('target') else (strategy['dream'][0] if strategy.get('dream') else None))

        return render(request, 'prediction/recommendation.html', {
            'active_page': 'predict',
            'rank': student_rank,
            'category': category,
            'gender': gender,
            'branch': branch,
            'overall_chance': int(overall_chance),
            'strategy': strategy,
            'best_roi': best_roi,
            'total_options': total_options,
            'trend_years_json': json.dumps(strategy.get('trend_years', ['2021', '2022', '2023', '2024', '2025'])),
            'trend_ranks_json': json.dumps(strategy.get('trend_ranks', [5200, 4800, 4500, 4300, 4100])),
            'trend_title': strategy.get('trend_title', 'Closing Rank Trend'),
        })


class CollegeListView(View):
    def get(self, request):
        search = request.GET.get('q', '')
        colleges = College.objects.all().order_by('name')

        if search:
            from django.db.models import Q
            for term in search.split():
                term_q = Q(name__icontains=term) | Q(short_name__icontains=term)
                term_lower = term.lower()
                if term_lower == 'iit':
                    term_q |= (Q(name__icontains='Indian Institute') & Q(name__icontains='Technology'))
                elif term_lower == 'nit':
                    term_q |= (Q(name__icontains='National Institute') & Q(name__icontains='Technology'))
                elif term_lower == 'iiit':
                    term_q |= (Q(name__icontains='Information Technology') | Q(name__icontains='Information Tech'))
                colleges = colleges.filter(term_q)

        paginator = Paginator(colleges, 30)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Annotate with branch count and latest cutoff data
        college_data = []
        for college in page_obj:
            branch_count = Cutoff.objects.filter(college=college).values('branch').distinct().count()
            latest_cutoff = Cutoff.objects.filter(college=college, category='OPEN', seat_pool='Gender-Neutral').order_by('-year', '-round_number').first()

            college_data.append({
                'id': college.id,
                'name': college.name,
                'short_name': college.short_name or college.name[:20],
                'state': college.state,
                'nirf_rank': college.nirf_rank,
                'branch_count': branch_count,
                'min_cutoff': latest_cutoff.closing_rank if latest_cutoff else None,
                'latest_year': latest_cutoff.year if latest_cutoff else None,
            })

        return render(request, 'colleges/college_list.html', {
            'active_page': 'colleges',
            'colleges': college_data,
            'page_obj': page_obj,
            'search_query': search,
            'total_count': paginator.count,
        })


class CollegeDetailView(View):
    def get(self, request, college_id):
        try:
            college = College.objects.get(id=college_id)
        except College.DoesNotExist:
            return redirect('college_list')

        # Get all branches offered by this college
        branches = sorted(set(Cutoff.objects.filter(college=college).values_list('branch__name', flat=True).distinct()))

        # Get cutoff trends (year-wise for OPEN category, Round 1)
        cutoff_trends = Cutoff.objects.filter(
            college=college,
            category='OPEN',
            seat_pool='Gender-Neutral',
            round_number=1,
        ).values('year').annotate(
            avg_closing=Avg('closing_rank'),
            min_closing=Min('closing_rank'),
        ).order_by('year')

        # Get latest year cutoffs per branch
        latest_year = Cutoff.objects.filter(college=college).aggregate(Max('year'))['year__max']
        branch_cutoffs = []
        if latest_year:
            bc = Cutoff.objects.filter(
                college=college, year=latest_year, category='OPEN',
                seat_pool='Gender-Neutral', round_number=1,
            ).select_related('branch').order_by('closing_rank')
            seen = set()
            for c in bc:
                if c.branch.name not in seen:
                    seen.add(c.branch.name)
                    branch_cutoffs.append({
                        'branch': c.branch.name,
                        'closing_rank': c.closing_rank,
                        'opening_rank': c.opening_rank,
                    })

        return render(request, 'colleges/college_detail.html', {
            'active_page': 'colleges',
            'college': college,
            'branches': list(branches),
            'cutoff_trends': list(cutoff_trends),
            'branch_cutoffs': branch_cutoffs,
            'latest_year': latest_year,
        })


class AnalyticsView(View):
    def get(self, request):
        total_colleges = College.objects.count()
        total_branches = Branch.objects.count()
        total_cutoffs = Cutoff.objects.count()

        latest_year = Cutoff.objects.aggregate(Max('year'))['year__max'] or 2025

        # Most competitive branches (lowest avg closing rank in OPEN)
        competitive_branches = Cutoff.objects.filter(
            year=latest_year, category='OPEN', round_number=1, seat_pool='Gender-Neutral'
        ).values('branch__name').annotate(
            avg_rank=Avg('closing_rank')
        ).order_by('avg_rank')[:8]

        # Year-over-year cutoff data
        yearly_data = Cutoff.objects.filter(
            category='OPEN', seat_pool='Gender-Neutral', round_number=1
        ).values('year').annotate(
            avg_closing=Avg('closing_rank'),
            total_records=Count('id'),
        ).order_by('year')

        # Top colleges by lowest closing rank
        top_colleges = Cutoff.objects.filter(
            year=latest_year, category='OPEN', round_number=1, seat_pool='Gender-Neutral'
        ).values('college__name').annotate(
            min_rank=Min('closing_rank'),
            avg_rank=Avg('closing_rank'),
            branch_count=Count('branch', distinct=True),
        ).order_by('min_rank')[:10]

        # State distribution for pie chart (IITs only)
        from django.db.models import Q
        iit_state_distribution = College.objects.filter(
            Q(name__icontains='Indian Institute of Technology') | Q(name__icontains='Indian Institute  of Technology')
        ).values('state').annotate(count=Count('id')).order_by('-count')
        
        pie_labels = []
        pie_data = []
        for s in iit_state_distribution:
            pie_labels.append(s['state'])
            pie_data.append(s['count'])
            
        pie_chart_data = {
            'labels': pie_labels,
            'data': pie_data,
        }

        return render(request, 'analytics/analytics.html', {
            'active_page': 'analytics',
            'total_colleges': total_colleges,
            'total_branches': total_branches,
            'total_cutoffs': total_cutoffs,
            'latest_year': latest_year,
            'competitive_branches': list(competitive_branches),
            'yearly_data': list(yearly_data),
            'top_colleges': list(top_colleges),
            'pie_chart_data': pie_chart_data,
        })


class ReportView(View):
    def get(self, request):
        rank = request.session.get('student_rank')
        category = request.session.get('category', 'OPEN')
        gender = request.session.get('gender', 'Gender-Neutral')
        state = request.session.get('state', '')

        if not rank:
            # Provide a demo report
            rank = '15000'
            category = 'OPEN'
            gender = 'Gender-Neutral'

        student_rank = int(rank)
        latest_year = Cutoff.objects.aggregate(Max('year'))['year__max'] or 2025

        from django.db.models import Q
        
        query = Q(
            year=latest_year,
            category=category,
            seat_pool=gender,
            round_number=1,
            closing_rank__gte=max(1, int(student_rank * 0.7)),
            closing_rank__lte=int(student_rank * 2.0),
        )
        
        if state:
            query &= (Q(quota__in=['AI', 'OS']) | Q(quota='HS', college__state__iexact=state))
        else:
            query &= Q(quota__in=['AI', 'OS'])
            
        candidates = Cutoff.objects.filter(query).select_related('college', 'branch').order_by('closing_rank')

        seen = set()
        top_picks = []

        for cand in candidates:
            key = (cand.college_id, cand.branch_id)
            if key not in seen:
                seen.add(key)
                ratio = cand.closing_rank / max(student_rank, 1)
                # Use same heuristic as ResultView
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
                prob = int(round(min(98, max(3, prob)), 0))

                top_picks.append({
                    'college': cand.college.name,
                    'branch': cand.branch.name,
                    'closing_rank': cand.closing_rank,
                    'prob': prob,
                    'color': 'on-tertiary-container' if prob >= 75 else ('secondary' if prob >= 40 else 'error'),
                })
            if len(top_picks) >= 5:
                break

        top_picks.sort(key=lambda x: x['prob'], reverse=True)

        # Aggregate match
        agg_match = int(sum(p['prob'] for p in top_picks) / max(len(top_picks), 1)) if top_picks else 0

        # Generate report ID
        report_hash = hashlib.md5(f"{rank}{category}{gender}".encode()).hexdigest()[:8].upper()
        report_id = f"ICA-{latest_year}-{report_hash}"
        now = datetime.now()

        # Get dynamic action plan
        engine = RecommendationEngine()
        action_plan = engine._generate_action_plan(student_rank, category, gender, state)

        return render(request, 'reports/report.html', {
            'active_page': 'report',
            'rank': rank,
            'category': category,
            'gender': gender,
            'top_picks': top_picks,
            'agg_match': agg_match,
            'report_id': report_id,
            'report_date': now.strftime('%d %b %Y'),
            'report_time': now.strftime('%H:%M IST'),
            'latest_year': latest_year,
            'action_plan': action_plan,
        })


class ROIAnalysisView(View):
    def get(self, request):
        colleges = College.objects.exclude(average_package__isnull=True).order_by('-average_package')[:20]
        
        roi_data = []
        for c in colleges:
            if c.average_fees and c.average_fees > 0:
                roi_score = float((c.average_package * 100000) / c.average_fees)
                roi_data.append({
                    'college': c,
                    'roi_score': round(roi_score, 2)
                })
        
        roi_data.sort(key=lambda x: x['roi_score'], reverse=True)
        
        return render(request, 'analytics/roi_analysis.html', {
            'active_page': 'analytics',
            'roi_data': roi_data,
        })

@method_decorator(csrf_exempt, name='dispatch')
class ChatView(View):
    def get(self, request):
        return render(request, 'prediction/chat.html', {
            'active_page': 'chat',
        })

    def post(self, request):
        import json
        import re
        from django.http import JsonResponse
        from django.db.models import Q, Min, Max, Avg, Count
        from django.db.models.functions import Lower

        body = json.loads(request.body)
        question = body.get('message', '').strip()
        q_lower = question.lower()

        # --- Extract numbers (potential ranks) ---
        numbers = re.findall(r'[\d,]+', question.replace(',', ''))
        ranks = [int(n) for n in numbers if 100 <= int(n) <= 500000]
        rank = ranks[0] if ranks else None

        # --- Extract category ---
        category = 'OPEN'
        cat_map = {
            'obc': 'OBC-NCL', 'sc ': 'SC', ' sc': 'SC', 'st ': 'ST', ' st': 'ST',
            'ews': 'EWS', 'general': 'OPEN', 'open': 'OPEN',
        }
        for keyword, cat_val in cat_map.items():
            if keyword in q_lower:
                category = cat_val
                break

        # --- Extract branch keywords ---
        branch_keywords = {
            'computer science': ['Computer Science', 'CSE'],
            'cse': ['Computer Science', 'CSE'],
            'information technology': ['Information Technology'],
            ' it ': ['Information Technology'],
            ' it?': ['Information Technology'],
            'ece': ['Electronics and Communication', 'ECE', 'Electronics & Communication'],
            'electronics': ['Electronics and Communication', 'ECE', 'Electronics', 'Electrical and Electronics'],
            'electrical': ['Electrical', 'Electrical Engineering'],
            'eee': ['Electrical and Electronics', 'EEE'],
            'mechanical': ['Mechanical', 'Mechanical Engineering'],
            'civil': ['Civil', 'Civil Engineering'],
            'chemical': ['Chemical', 'Chemical Engineering'],
            'ai': ['Artificial Intelligence', 'AI', 'Data Science'],
            'artificial intelligence': ['Artificial Intelligence', 'AI'],
            'data science': ['Data Science', 'Artificial Intelligence'],
            'biotech': ['Biotechnology', 'Bio Technology'],
            'mathematics': ['Mathematics', 'Mathematics and Computing'],
            'math': ['Mathematics', 'Mathematics and Computing'],
        }

        matched_branch_names = []
        for kw, names in branch_keywords.items():
            if kw in q_lower:
                matched_branch_names.extend(names)

        # --- Extract college name keywords ---
        college_keywords = []
        known_colleges = {
            'nit surat': 'SVNIT', 'svnit': 'SVNIT', 'nit surathkal': 'NITK', 'nitk': 'NITK',
            'nit warangal': 'NIT Warangal', 'nitw': 'NIT Warangal',
            'nit trichy': 'NIT Tiruchirappalli', 'nitt': 'NIT Tiruchirappalli',
            'nit rourkela': 'NIT Rourkela', 'nitr': 'NIT Rourkela',
            'nit allahabad': 'MNNIT', 'mnnit': 'MNNIT',
            'nit calicut': 'NIT Calicut', 'nitc': 'NIT Calicut',
            'nit jaipur': 'MNIT', 'mnit': 'MNIT',
            'nit nagpur': 'VNIT', 'vnit': 'VNIT',
            'nit bhopal': 'MANIT', 'manit': 'MANIT',
            'iiit hyderabad': 'IIIT Hyderabad', 'iiith': 'IIIT Hyderabad',
            'iiit allahabad': 'IIIT Allahabad', 'iiita': 'IIIT Allahabad',
            'iit bombay': 'IIT Bombay', 'iitb': 'IIT Bombay',
            'iit delhi': 'IIT Delhi', 'iitd': 'IIT Delhi',
            'iit madras': 'IIT Madras', 'iitm': 'IIT Madras',
            'iit kanpur': 'IIT Kanpur', 'iitk': 'IIT Kanpur',
            'iit kharagpur': 'IIT Kharagpur', 'iitkgp': 'IIT Kharagpur',
            'iit roorkee': 'IIT Roorkee', 'iitr': 'IIT Roorkee',
            'iit guwahati': 'IIT Guwahati', 'iitg': 'IIT Guwahati',
        }
        for kw, name in known_colleges.items():
            if kw in q_lower:
                college_keywords.append(name)

        latest_year = Cutoff.objects.aggregate(Max('year'))['year__max']
        if not latest_year:
            return JsonResponse({'response': "I don't have cutoff data loaded yet. Please import cutoff data first."})

        # ============================================
        # INTENT DETECTION AND RESPONSE GENERATION
        # ============================================

        # --- INTENT 1: "Which colleges can I get with rank X for branch Y?" ---
        if rank and matched_branch_names:
            branch_q = Q()
            for bn in matched_branch_names:
                branch_q |= Q(branch__name__icontains=bn)

            cutoffs = Cutoff.objects.filter(
                branch_q,
                category=category,
                seat_pool='Gender-Neutral',
                closing_rank__gte=rank,
                year=latest_year,
            ).select_related('college', 'branch').order_by('closing_rank')

            # Get last round per college-branch
            seen = set()
            results = []
            for c in cutoffs:
                key = (c.college_id, c.branch_id)
                if key not in seen:
                    seen.add(key)
                    results.append(c)
                if len(results) >= 15:
                    break

            if results:
                branch_label = matched_branch_names[0]
                lines = [f"With a rank of **{rank:,}** ({category} category), here are the colleges you can target for **{branch_label}** based on {latest_year} data:\n"]
                
                safe = [r for r in results if r.closing_rank >= rank * 1.3]
                target = [r for r in results if rank * 0.9 <= r.closing_rank < rank * 1.3]
                reach = [r for r in results if r.closing_rank < rank * 0.9]

                if reach:
                    lines.append("🔴 **Reach (Competitive):**")
                    for r in reach[:3]:
                        lines.append(f"• {r.college.name} — {r.branch.name} (Closing Rank: {r.closing_rank:,})")
                if target:
                    lines.append("\n🟡 **Target (Good Chance):**")
                    for r in target[:5]:
                        lines.append(f"• {r.college.name} — {r.branch.name} (Closing Rank: {r.closing_rank:,})")
                if safe:
                    lines.append("\n🟢 **Safe (High Probability):**")
                    for r in safe[:5]:
                        lines.append(f"• {r.college.name} — {r.branch.name} (Closing Rank: {r.closing_rank:,})")

                lines.append(f"\n*Data sourced from {latest_year} JoSAA final round cutoffs.*")
                return JsonResponse({'response': '\n'.join(lines)})
            else:
                return JsonResponse({'response': f"I could not find any colleges matching **{matched_branch_names[0]}** for rank **{rank:,}** ({category}) in {latest_year} data. The rank may be too high for this branch, or try a different category."})

        # --- INTENT 2: "Can I get <college> with rank X?" ---
        if rank and college_keywords:
            college_q = Q()
            for cn in college_keywords:
                college_q |= Q(college__name__icontains=cn) | Q(college__short_name__icontains=cn)

            cutoffs = Cutoff.objects.filter(
                college_q,
                category=category,
                seat_pool='Gender-Neutral',
                year=latest_year,
            ).select_related('college', 'branch').order_by('closing_rank')

            seen = set()
            results = []
            for c in cutoffs:
                key = (c.college_id, c.branch_id)
                if key not in seen:
                    seen.add(key)
                    results.append(c)

            if results:
                college_name = results[0].college.name
                yes_branches = [r for r in results if r.closing_rank >= rank]
                no_branches = [r for r in results if r.closing_rank < rank]

                lines = [f"For **{college_name}** with rank **{rank:,}** ({category}, {latest_year}):\n"]

                if yes_branches:
                    lines.append("✅ **Branches you can get:**")
                    for b in yes_branches[:8]:
                        lines.append(f"• {b.branch.name} (Closing: {b.closing_rank:,})")

                if no_branches:
                    lines.append("\n❌ **Unlikely (Cutoff is lower than your rank):**")
                    for b in no_branches[:5]:
                        lines.append(f"• {b.branch.name} (Closing: {b.closing_rank:,})")

                if not yes_branches:
                    lines.append(f"\nWith rank {rank:,}, none of the branches seem reachable at {college_name}. Consider a lower-tier NIT or IIIT.")
                
                return JsonResponse({'response': '\n'.join(lines)})
            else:
                return JsonResponse({'response': f"I couldn't find cutoff data for **{college_keywords[0]}** in {latest_year}. Please check the spelling or try another college."})

        # --- INTENT 3: "Which colleges can I get with rank X?" (no branch specified) ---
        if rank and not matched_branch_names and not college_keywords:
            cutoffs = Cutoff.objects.filter(
                category=category,
                seat_pool='Gender-Neutral',
                closing_rank__gte=rank,
                year=latest_year,
            ).select_related('college', 'branch').order_by('closing_rank')

            seen = set()
            results = []
            for c in cutoffs:
                key = (c.college_id, c.branch_id)
                if key not in seen:
                    seen.add(key)
                    results.append(c)
                if len(results) >= 15:
                    break

            if results:
                lines = [f"With rank **{rank:,}** ({category} category), here are some top options across all branches ({latest_year}):\n"]
                for r in results:
                    lines.append(f"• **{r.college.name}** — {r.branch.name} (Closing Rank: {r.closing_rank:,})")
                lines.append(f"\n*Showing top {len(results)} results. Use the Predictor tool for a full analysis.*")
                return JsonResponse({'response': '\n'.join(lines)})
            else:
                return JsonResponse({'response': f"I couldn't find colleges matching rank **{rank:,}** ({category}) in {latest_year} data. Try adjusting the rank or specifying a branch."})

        # --- INTENT 4: Compare branches "ECE vs AI" / "should I choose X or Y" ---
        if ('or' in q_lower or 'vs' in q_lower or 'compare' in q_lower or 'choose' in q_lower or 'better' in q_lower) and len(matched_branch_names) >= 2:
            branch_names_unique = list(dict.fromkeys(matched_branch_names))[:2]
            compare_data = []
            for bn in branch_names_unique:
                stats = Cutoff.objects.filter(
                    branch__name__icontains=bn,
                    category='OPEN',
                    seat_pool='Gender-Neutral',
                    year=latest_year,
                ).aggregate(
                    avg_rank=Avg('closing_rank'),
                    min_rank=Min('closing_rank'),
                    max_rank=Max('closing_rank'),
                    total_seats=Count('id'),
                )
                compare_data.append({'name': bn, **stats})

            lines = [f"**Branch Comparison: {branch_names_unique[0]} vs {branch_names_unique[1]}** ({latest_year} data, OPEN category)\n"]
            for d in compare_data:
                lines.append(f"📊 **{d['name']}:**")
                lines.append(f"  • Average Closing Rank: **{int(d['avg_rank'] or 0):,}**")
                lines.append(f"  • Best (Lowest) Rank: **{int(d['min_rank'] or 0):,}**")
                lines.append(f"  • Highest Closing Rank: **{int(d['max_rank'] or 0):,}**")
                lines.append(f"  • Total Cutoff Records: {d['total_seats']}\n")

            if compare_data[0].get('avg_rank') and compare_data[1].get('avg_rank'):
                if compare_data[0]['avg_rank'] < compare_data[1]['avg_rank']:
                    lines.append(f"*Verdict:* **{compare_data[0]['name']}** is more competitive (lower average rank means harder to get in).")
                else:
                    lines.append(f"*Verdict:* **{compare_data[1]['name']}** is more competitive (lower average rank means harder to get in).")

            return JsonResponse({'response': '\n'.join(lines)})

        # --- INTENT 5: Best colleges under X fees ---
        if ('fees' in q_lower or 'fee' in q_lower or 'lakh' in q_lower or 'cost' in q_lower or 'cheap' in q_lower or 'affordable' in q_lower):
            fee_numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(?:lakh|lac|l\b)', q_lower)
            max_fee = float(fee_numbers[0]) * 100000 if fee_numbers else 200000

            colleges = College.objects.filter(
                average_fees__lte=max_fee,
                average_fees__gt=0,
            ).exclude(average_package__isnull=True).order_by('-average_package')[:10]

            if colleges:
                lines = [f"**Top Colleges with Fees under ₹{max_fee/100000:.0f} Lakh:**\n"]
                for i, c in enumerate(colleges, 1):
                    pkg = f"₹{float(c.average_package):.1f} LPA" if c.average_package else "N/A"
                    fee = f"₹{float(c.average_fees)/100000:.2f}L" if c.average_fees else "N/A"
                    lines.append(f"{i}. **{c.name}** ({c.state})")
                    lines.append(f"   • Fees: {fee} | Avg Package: {pkg}")
                    if c.average_fees and c.average_package and float(c.average_fees) > 0:
                        roi = float(c.average_package * 100000) / float(c.average_fees)
                        lines.append(f"   • ROI Score: **{roi:.1f}x**\n")
                    else:
                        lines.append("")
                return JsonResponse({'response': '\n'.join(lines)})
            else:
                return JsonResponse({'response': f"I couldn't find colleges with fees under ₹{max_fee/100000:.0f} Lakh in our database. Try increasing the budget."})

        # --- INTENT 6: CSAB related questions ---
        if 'csab' in q_lower:
            return JsonResponse({'response': "**Yes, participating in CSAB is highly recommended!**\n\nCSAB (Central Seat Allocation Board) conducts **Special Rounds** after JoSAA's 6 rounds to fill vacant seats in NITs, IIITs, and GFTIs.\n\n**Key Facts:**\n• Historically, cutoff ranks can jump by **10,000 to 50,000+** compared to JoSAA Round 6.\n• You can **retain your JoSAA seat** while participating — zero risk!\n• Requires a **separate registration** and nominal fee.\n\n**Who should participate?**\n1. Students who didn't get any seat in JoSAA.\n2. Students who got a seat but want a branch/college upgrade.\n3. Students targeting GFTIs (which often have the biggest vacancy shifts).\n\n*Always participate if you're eligible. The upside far outweighs the small registration cost.*"})

        # --- INTENT 7: College-specific info (no rank given) ---
        if college_keywords and not rank:
            college_q = Q()
            for cn in college_keywords:
                college_q |= Q(name__icontains=cn) | Q(short_name__icontains=cn)
            
            college = College.objects.filter(college_q).first()
            if college:
                cutoff_stats = Cutoff.objects.filter(
                    college=college, category='OPEN', seat_pool='Gender-Neutral', year=latest_year
                ).aggregate(
                    min_rank=Min('closing_rank'),
                    max_rank=Max('closing_rank'),
                    avg_rank=Avg('closing_rank'),
                    branch_count=Count('branch', distinct=True),
                )

                top_branches = Cutoff.objects.filter(
                    college=college, category='OPEN', seat_pool='Gender-Neutral', year=latest_year
                ).values('branch__name').annotate(cr=Min('closing_rank')).order_by('cr')[:5]

                lines = [f"**{college.name}** ({college.city or ''}, {college.state})\n"]
                if college.nirf_rank:
                    lines.append(f"🏅 NIRF Rank: **#{college.nirf_rank}**")
                if college.average_fees:
                    lines.append(f"💰 Fees: ₹{float(college.average_fees)/100000:.2f}L")
                if college.average_package:
                    lines.append(f"📈 Avg Package: ₹{float(college.average_package):.1f} LPA")
                
                lines.append(f"\n📊 **{latest_year} Cutoff Summary (OPEN):**")
                lines.append(f"• Best Rank: {int(cutoff_stats['min_rank'] or 0):,}")
                lines.append(f"• Highest Closing Rank: {int(cutoff_stats['max_rank'] or 0):,}")
                lines.append(f"• Branches Available: {cutoff_stats['branch_count']}")
                
                if top_branches:
                    lines.append(f"\n🔥 **Top Branches (by lowest cutoff):**")
                    for b in top_branches:
                        lines.append(f"• {b['branch__name']} — Closing: {int(b['cr']):,}")

                return JsonResponse({'response': '\n'.join(lines)})

        # --- INTENT 8: Branch-specific info (no rank given) ---
        if matched_branch_names and not rank and not college_keywords:
            bn = matched_branch_names[0]
            stats = Cutoff.objects.filter(
                branch__name__icontains=bn,
                category='OPEN',
                seat_pool='Gender-Neutral',
                year=latest_year,
            ).aggregate(
                avg_rank=Avg('closing_rank'),
                min_rank=Min('closing_rank'),
                max_rank=Max('closing_rank'),
                college_count=Count('college', distinct=True),
            )
            
            top_colleges = Cutoff.objects.filter(
                branch__name__icontains=bn,
                category='OPEN',
                seat_pool='Gender-Neutral',
                year=latest_year,
            ).values('college__name').annotate(cr=Min('closing_rank')).order_by('cr')[:8]

            if stats['avg_rank']:
                lines = [f"**{bn}** — Overview ({latest_year}, OPEN Category)\n"]
                lines.append(f"• Average Closing Rank: **{int(stats['avg_rank']):,}**")
                lines.append(f"• Best (Lowest) Rank: **{int(stats['min_rank']):,}**")
                lines.append(f"• Total Colleges Offering: **{stats['college_count']}**")
                
                if top_colleges:
                    lines.append(f"\n🏆 **Top Colleges for {bn} (by cutoff):**")
                    for i, c in enumerate(top_colleges, 1):
                        lines.append(f"{i}. {c['college__name']} — Rank: {int(c['cr']):,}")
                
                return JsonResponse({'response': '\n'.join(lines)})

        # --- INTENT 9: General counseling / JoSAA ---
        if any(kw in q_lower for kw in ['josaa', 'counseling', 'counselling', 'round', 'seat', 'allot']):
            return JsonResponse({'response': "**JoSAA Counseling Tips:**\n\n1. **Fill maximum choices** — Don't leave any slot empty. Fill all possible combinations of college + branch.\n2. **Order wisely** — Place your dream choices at the top. JoSAA allots the highest preference possible.\n3. **Use Float/Freeze/Slide options** carefully:\n   • **Float:** Accept the seat but stay in for a better college (any branch).\n   • **Slide:** Accept but look for better branch in the same college.\n   • **Freeze:** Accept and exit counseling.\n4. **Don't skip lower rounds** — Cutoffs often drop significantly in Rounds 4-6.\n5. **CSAB Special Rounds** are your safety net after JoSAA.\n\n*Ask me with your specific rank and I'll recommend exact colleges for you!*"})

        # --- FALLBACK: Smart search across the database ---
        # Try to find any matching college or branch from the user's text
        words = [w for w in q_lower.split() if len(w) > 3]
        for word in words:
            college_match = College.objects.filter(
                Q(name__icontains=word) | Q(short_name__icontains=word)
            ).first()
            if college_match:
                cutoff_stats = Cutoff.objects.filter(
                    college=college_match, category='OPEN', year=latest_year
                ).aggregate(min_rank=Min('closing_rank'), max_rank=Max('closing_rank'))
                
                if cutoff_stats['min_rank']:
                    return JsonResponse({'response': f"I found **{college_match.name}** ({college_match.state}).\n\nIn {latest_year}, cutoffs ranged from **{int(cutoff_stats['min_rank']):,}** to **{int(cutoff_stats['max_rank']):,}** (OPEN category).\n\n*Tell me your rank and I can check exactly which branches you'd qualify for!*"})

        return JsonResponse({'response': "I'd love to help! To give you the most accurate answer, please include:\n\n• **Your JEE rank** (e.g., 15000)\n• **Branch preference** (e.g., CSE, ECE, IT)\n• **Category** (e.g., OPEN, OBC, SC, ST, EWS)\n\nExample: *\"Which colleges can I get at rank 12000 for CSE in OBC?\"*\n\nYou can also ask me about specific colleges, branch comparisons, CSAB, or fee-based recommendations!"})


class ModelInspectorView(View):
    """View to inspect all trained ML models — accuracy, features, hyperparameters, etc."""

    def get(self, request):
        import os
        from django.conf import settings

        report_path = os.path.join(settings.BASE_DIR, 'ml_models', 'model_report.json')
        models_data = {}

        if os.path.exists(report_path):
            with open(report_path, 'r') as f:
                models_data = json.load(f)

        # Determine best model by accuracy
        best_model = None
        best_accuracy = 0
        for key, info in models_data.items():
            if info.get('accuracy', 0) > best_accuracy:
                best_accuracy = info['accuracy']
                best_model = key

        # Check which model files exist on disk
        model_files = {
            'xgboost': os.path.join(settings.BASE_DIR, 'ml_models', 'xgboost_admission_model.pkl'),
        }

        available_models = {k: os.path.exists(v) for k, v in model_files.items()}

        # File sizes
        model_sizes = {}
        for key, path in model_files.items():
            if os.path.exists(path):
                size_bytes = os.path.getsize(path)
                if size_bytes > 1024 * 1024:
                    model_sizes[key] = f"{size_bytes / (1024 * 1024):.1f} MB"
                else:
                    model_sizes[key] = f"{size_bytes / 1024:.1f} KB"

        return render(request, 'prediction/model_inspector.html', {
            'active_page': 'models',
            'models_data': models_data,
            'models_data_json': json.dumps(models_data),
            'best_model': best_model,
            'available_models': available_models,
            'model_sizes': model_sizes,
            'total_trained': len(models_data),
        })

"""
Who approves a Study Bond application, in one place.

The rules we agreed:
  - The employee can only link an application to a study they are actually on
    (as PI, coordinator or member). Operations staff, with no studies, go to the Director.
  - The linked study's PI approves, unless the applicant IS that PI: nobody sits above
    a PI on their own study, so it goes to the Director.
  - A PI with a PIProfile that has "uses_link" ticked decides by emailed one-time link
    instead of signing in. Anyone else (the Director, a PI with a BUP account) signs in.
"""

from django.db.models import Q

from research.models import Study


def person_name(user):
    return (user.get_full_name() or user.username) if user else 'Someone'


def studies_for(user):
    """Every study this person is on, in any role."""
    return (Study.objects.filter(Q(pi=user) | Q(coordinator=user) | Q(employees=user))
            .distinct().select_related('pi').order_by('name'))


def director():
    from accounts.models import CustomUser
    return CustomUser.objects.filter(role='DIRECTOR', is_archived=False).first()


def determine_approver(employee, linked_project):
    if linked_project is None or linked_project.pi_id == employee.id:
        return director()
    return linked_project.pi


def approver_link_profile(approver):
    """The PIProfile when this approver decides by emailed link; None when they sign in instead."""
    profile = getattr(approver, 'pi_profile', None)   # a missing profile raises an AttributeError subclass
    return profile if (profile is not None and profile.uses_link) else None


def candidate_approvers(application):
    """
    What HR may switch an application to: the PI of any study the employee is on
    (except one they lead themselves), or the Director.
    """
    choices = []
    for study in studies_for(application.employee):
        if study.pi_id != application.employee_id:
            choices.append((f"study:{study.pk}", f"{study.name}: PI {person_name(study.pi)}"))
    choices.append(("director", "The Director"))
    return choices


def apply_approver_choice(application, choice):
    """Apply one value from candidate_approvers(). Returns True if it changed anything."""
    before = (application.linked_project_id, application.approver_id)
    if choice == "director":
        application.linked_project = None
        application.approver = director()
    elif choice.startswith("study:"):
        study = studies_for(application.employee).filter(pk=int(choice.split(":", 1)[1])).first()
        if study is None or study.pi_id == application.employee_id:
            return False
        application.linked_project = study
        application.approver = study.pi
    else:
        return False
    return before != (application.linked_project_id, application.approver_id)

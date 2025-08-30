def is_role(user, role: str) -> bool:
    """
    Checks whether a user belongs to a role/group.
    Special case: 'admin' is mapped to superuser.
    """
    role = role.strip().lower()
    if role == 'admin':
        return user.is_superuser
    return user.groups.filter(name__iexact=role).exists()


def get_role(user):
    """
    Returns the role name string for the user.
    If not in a known group, falls back to 'customer' or 'anonymous'.
    """
    roles = ['admin', 'manager', 'delivery']
    for role in roles:
        if is_role(user, role):
            return role
    return 'customer' if user.is_authenticated else 'anonymous'
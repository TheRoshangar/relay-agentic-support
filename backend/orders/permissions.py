def is_support_agent(user):
    return user.is_authenticated and user.groups.filter(name="support_agent").exists()
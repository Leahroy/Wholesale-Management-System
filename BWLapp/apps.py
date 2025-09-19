from django.apps import AppConfig


class BwlappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'BWLapp'
    
    def ready(self):
        import BWLapp.signals
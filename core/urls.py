from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .tokens import MemberTokenObtainPairView
from .views import MemberDeactivateView, MemberDetailView, MemberListCreateView, ShareAdjustView

urlpatterns = [
    # Auth
    path('auth/token/', MemberTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Members
    path('members/', MemberListCreateView.as_view(), name='member_list_create'),
    path('members/<uuid:pk>/', MemberDetailView.as_view(), name='member_detail'),
    path('members/<uuid:pk>/deactivate/', MemberDeactivateView.as_view(), name='member_deactivate'),

    # Shares
    path('shares/adjust/', ShareAdjustView.as_view(), name='share_adjust'),
]

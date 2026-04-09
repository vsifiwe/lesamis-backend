from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Member
from .permissions import IsAdminUser
from .serializers import CreateMemberSerializer, MemberSerializer


class MemberListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        members = Member.objects.all()
        serializer = MemberSerializer(members, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CreateMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        return Response(MemberSerializer(member).data, status=status.HTTP_201_CREATED)


class MemberDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        return Response(MemberSerializer(member).data)


class MemberDeactivateView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        if member.status == Member.Status.EXITED:
            return Response(
                {'detail': 'Member has already exited.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        member.status = Member.Status.EXITED
        member.exit_date = member.exit_date or timezone.now().date()
        member.save(update_fields=['status', 'exit_date', 'updated_at'])
        return Response(MemberSerializer(member).data)

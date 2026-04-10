# Generated manually: 每用户每景点仅一条推荐反馈

from django.db import migrations, models


def _dedupe_likerecommend(apps, schema_editor):
    LikeRecommendSight = apps.get_model('travel', 'LikeRecommendSight')
    seen = set()
    for row in LikeRecommendSight.objects.all().order_by('id'):
        key = (row.user_id, row.sight_id)
        if key in seen:
            row.delete()
        else:
            seen.add(key)


class Migration(migrations.Migration):

    dependencies = [
        ('travel', '0008_bookinghotel_check_in_bookinghotel_check_out_and_more'),
    ]

    operations = [
        migrations.RunPython(_dedupe_likerecommend, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='likerecommendsight',
            constraint=models.UniqueConstraint(
                fields=('user', 'sight'),
                name='uniq_likerecommend_user_sight',
            ),
        ),
    ]

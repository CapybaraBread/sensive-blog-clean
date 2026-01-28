from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models import Count
class TagQuerySet(models.QuerySet):
    def popular(self):
        return self.annotate(
            posts_with_tag=models.Count('posts')
        ).order_by('-posts_with_tag')

class PostQuerySet(models.QuerySet):
    def popular(self):
        return self.annotate(
            likes_amount=Count('likes')
        ).order_by('-likes_amount')

    def fetch_with_comments_count(self):
        posts = list(self)
        if not posts:
            return posts
        post_ids = [post.id for post in posts]
        comments_counts = (
            self.model.objects
            .filter(id__in=post_ids)
            .annotate(comments_amount=Count('comments'))
            .values_list('id', 'comments_amount')
        )
        count_for_id = dict(comments_counts)
        for post in posts:
            post.comments_amount = count_for_id.get(post.id, 0)
        return posts
        # fetch_with_comments_count считает количество комментариев отдельным запросом, а не через annotate() в основном queryset.

        # Зачем это нужно и чем лучше annotate:

        # – Не ломает подсчёты, когда queryset уже содержит JOIN’ы (лайки, теги, фильтры).
        # annotate(Count('comments')) в таких случаях часто врёт из-за умножения строк.

        # – Не усложняет исходный SQL.
        # Основной запрос остаётся таким, каким ты его задумал, без лишних GROUP BY и DISTINCT.

        # – Работает стабильно с уже отсортированными, отфильтрованными и пагинированными постами.
        # Счётчик просто “приклеивается” к готовым объектам.

        # Когда использовать:

        # – Если в queryset уже есть annotate, prefetch, сложные JOIN’ы
        # – Если Count(..., distinct=True) начинает душить базу
        # – Если важна корректность счётчиков, а не “один запрос любой ценой”

        # Когда не использовать:

        # – Если нужен queryset для дальнейших фильтров/сортировок
        # – Если простая выборка и обычный annotate работает корректно

        # Итог:
        # annotate — быстрее и чище в простых случаях.
        # fetch_with_comments_count — надёжнее в сложных.

class Post(models.Model):
    objects = PostQuerySet.as_manager()
    title = models.CharField('Заголовок', max_length=200)
    text = models.TextField('Текст')
    slug = models.SlugField('Название в виде url', max_length=200)
    image = models.ImageField('Картинка')
    published_at = models.DateTimeField('Дата и время публикации')

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        limit_choices_to={'is_staff': True})
    likes = models.ManyToManyField(
        User,
        related_name='liked_posts',
        verbose_name='Кто лайкнул',
        blank=True)
    tags = models.ManyToManyField(
        'Tag',
        related_name='posts',
        verbose_name='Теги')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', args={'slug': self.slug})

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'пост'
        verbose_name_plural = 'посты'


class Tag(models.Model):
    objects = TagQuerySet.as_manager()
    title = models.CharField('Тег', max_length=20, unique=True)

    def __str__(self):
        return self.title

    def clean(self):
        self.title = self.title.lower()

    def get_absolute_url(self):
        return reverse('tag_filter', args={'tag_title': self.slug})

    class Meta:
        ordering = ['title']
        verbose_name = 'тег'
        verbose_name_plural = 'теги'


class Comment(models.Model):
    post = models.ForeignKey(
        'Post',
        related_name='comments',
        on_delete=models.CASCADE,
        verbose_name='Пост, к которому написан')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор')

    text = models.TextField('Текст комментария')
    published_at = models.DateTimeField('Дата и время публикации')

    def __str__(self):
        return f'{self.author.username} under {self.post.title}'

    class Meta:
        ordering = ['published_at']
        verbose_name = 'комментарий'
        verbose_name_plural = 'комментарии'

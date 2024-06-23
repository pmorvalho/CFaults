#include <stdio.h>

int main()
{
  int f,s,t;

  scanf("%d%d%d", &f,&s,&t);

  if (f < s && f >= t)
    printf("%d",f);
  if (f > s && s <= t)
    printf("%d",s);
  if (f > t && s > t)
    printf("%d",t);

  return 0;
}

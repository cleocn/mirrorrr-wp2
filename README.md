== copy from ==

[https://github.com/bslatkin/mirrorrr](https://github.com/bslatkin/mirrorrr)



== 使用镜像安装pypi包 ==

python -m pip install requests -i http://pypi.doubanio.com/simple/  --trusted-host pypi.doubanio.com

python -m pip install webapp2 -i http://pypi.doubanio.com/simple/  --trusted-host pypi.doubanio.com

python -m pip install WebOb -i http://pypi.doubanio.com/simple/  --trusted-host pypi.doubanio.com

python -m pip install Paste -i http://pypi.doubanio.com/simple/  --trusted-host pypi.doubanio.com

python -m pip install python-memcached -i http://pypi.doubanio.com/simple/  --trusted-host pypi.doubanio.com

python -m pip install Jinja2 -i http://pypi.doubanio.com/simple/  --trusted-host pypi.doubanio.com

python -m pip install livereload -i http://pypi.doubanio.com/simple/  --trusted-host pypi.doubanio.com

python -m pip install supervisor -i http://pypi.doubanio.com/simple/  --trusted-host pypi.doubanio.com
 




== 其他 == 

windows 下面的memcahced： 
http://www.cnblogs.com/Li-Cheng/p/4392294.html


==  RUN ==

python pymonitor.py mirror_cp.py

打开 http://localhost:7878/

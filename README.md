# Gaz Tüpü Yönetim Sistemi – başlangıç sürümü

Bu paket, mobil uyumlu Flask + PostgreSQL uygulamasının ilk geliştirme iskeletidir. Henüz üretim ortamına alınmış veya mevcut SQLite verileri aktarılmış değildir.

## Yerel deneme
1. Python 3.11+ kurun.
2. Sanal ortam oluşturup etkinleştirin: `python -m venv .venv`
3. Paketleri kurun: `pip install -r requirements.txt`
4. Yönetici bilgilerini ortam değişkeni olarak tanımlayın (`ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SECRET_KEY`).
5. `flask --app app init-db` komutunu çalıştırın.
6. `python app.py` ile başlatın ve `http://127.0.0.1:5000` adresini açın.

## Buluta yayınlama (Render örneği)
- GitHub'a bu proje dosyalarını yükleyin.
- Render'da PostgreSQL veritabanı ve Web Service oluşturun.
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app`
- Environment Variables: `SECRET_KEY`, `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `COOKIE_SECURE=1`.
- İlk kurulumda Render Shell üzerinden `flask --app app init-db` çalıştırın.
- Üretim kullanımı için ücretli/kalıcı veritabanı, yedekleme ve erişim kontrolleri etkinleştirilmelidir.

## Önemli
- ZIP içindeki eski SQLite veritabanı otomatik olarak PostgreSQL'e taşınmaz. Eski tablolar, ilişkiler, görünümler, tetikleyiciler ve kayıtlar için ayrıca kontrollü geçiş/migrasyon gerekir.
- Bu sürümde giriş, rol bazlı yönetici kullanıcı ekleme, temel gösterge paneli ve işlem günlüğü iskeleti vardır. Stok, müşteri, tüp, sipariş ve barkod ekranları sonraki geliştirme adımlarıdır.
- `SECRET_KEY` ve yönetici şifresini kaynak koda yazmayın; sunucu ortam değişkenlerinde saklayın. Gerçek kullanıcı parolalarını paylaşmayın.
- İnternete açmadan önce CSRF koruması, hız sınırlama, parola sıfırlama, yedekleme/geri yükleme testi ve güvenlik denetimi tamamlanmalıdır.

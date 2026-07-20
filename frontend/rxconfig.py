import reflex as rx

# The compile-time default theme; the owner's saved colours arrive at runtime and
# are published as CSS variables that re-theme the whole page (see shop/shop.py).
# The dev server's event backend runs on 8001 so it doesn't clash with the API.
config = rx.Config(
    app_name="shop",
    frontend_port=3000,
    backend_port=8001,
    plugins=[
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                appearance="light",
                accent_color="bronze",
                gray_color="sand",
                radius="large",
            )
        ),
        rx.plugins.SitemapPlugin(),
    ],
)

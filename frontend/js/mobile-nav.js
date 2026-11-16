(function () {
    function onReady(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    function wrapTables() {
        document.querySelectorAll('table').forEach(function (table) {
            if (table.parentElement && table.parentElement.classList.contains('table-scroll')) {
                return;
            }
            var wrap = document.createElement('div');
            wrap.className = 'table-scroll';
            table.parentNode.insertBefore(wrap, table);
            wrap.appendChild(table);
        });
    }

    function setupSidebar() {
        var sidebar = document.querySelector('.sidebar');
        var navbarContent = document.querySelector('.navbar-content') || document.querySelector('.navbar');
        if (!sidebar || !navbarContent) {
            return;
        }
        if (document.querySelector('.mobile-menu-btn')) {
            return;
        }

        var left = document.createElement('div');
        left.className = 'navbar-left';
        navbarContent.insertBefore(left, navbarContent.firstChild);

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'mobile-menu-btn';
        btn.setAttribute('aria-label', 'Open navigation');
        btn.setAttribute('aria-expanded', 'false');
        btn.innerHTML = '<i class="fas fa-bars"></i>';
        left.appendChild(btn);

        var logo = navbarContent.querySelector('.logo');
        if (logo) {
            left.appendChild(logo);
        }

        var backdrop = document.createElement('div');
        backdrop.className = 'sidebar-backdrop';
        document.body.appendChild(backdrop);

        function setOpen(open) {
            sidebar.classList.toggle('open', open);
            backdrop.classList.toggle('show', open);
            document.body.classList.toggle('nav-open', open);
            btn.setAttribute('aria-expanded', open ? 'true' : 'false');
            btn.innerHTML = open ? '<i class="fas fa-times"></i>' : '<i class="fas fa-bars"></i>';
        }

        btn.addEventListener('click', function (event) {
            event.stopPropagation();
            setOpen(!sidebar.classList.contains('open'));
        });

        backdrop.addEventListener('click', function () {
            setOpen(false);
        });

        sidebar.addEventListener('click', function (event) {
            if (event.target.closest('a')) {
                setOpen(false);
            }
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                setOpen(false);
            }
        });

        window.addEventListener('resize', function () {
            if (window.innerWidth > 1024) {
                setOpen(false);
            }
        });
    }

    function observeTables() {
        if (!window.MutationObserver) {
            return;
        }
        var pending = false;
        var observer = new MutationObserver(function (mutations) {
            var hasTable = mutations.some(function (mutation) {
                return Array.prototype.some.call(mutation.addedNodes, function (node) {
                    return node.nodeType === 1 && (node.tagName === 'TABLE' || node.querySelector('table'));
                });
            });
            if (!hasTable || pending) {
                return;
            }
            pending = true;
            window.setTimeout(function () {
                pending = false;
                wrapTables();
            }, 50);
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    onReady(function () {
        if (document.querySelector('.main-content')) {
            document.body.classList.add('has-main-content');
        }
        wrapTables();
        observeTables();
        setupSidebar();
    });
})();

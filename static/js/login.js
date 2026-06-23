(function () {
    function setActiveSlide(slides, index) {
        for (var i = 0; i < slides.length; i += 1) {
            slides[i].classList.toggle('is-active', i === index);
        }
    }

    function initLoginCarousel() {
        var slides = document.querySelectorAll('.login-bg-slide');
        if (!slides.length || slides.length === 1) {
            return;
        }

        var index = 0;
        setActiveSlide(slides, index);

        window.setInterval(function () {
            index = (index + 1) % slides.length;
            setActiveSlide(slides, index);
        }, 7000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initLoginCarousel);
    } else {
        initLoginCarousel();
    }
})();

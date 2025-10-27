document.addEventListener('DOMContentLoaded', () => {
    const sliders = document.querySelectorAll('.before-after-slider');
    sliders.forEach(slider => {
        const before = slider.querySelector('.before');
        const handle = slider.querySelector('.slider-handle');
        let isDragging = false;

        handle.addEventListener('mousedown', () => {
            isDragging = true;
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const rect = slider.getBoundingClientRect();
            let x = e.clientX - rect.left;
            if (x < 0) x = 0;
            if (x > rect.width) x = rect.width;
            const percentage = (x / rect.width) * 100;
            before.style.clipPath = `polygon(0 0, ${percentage}% 0, ${percentage}% 100%, 0 100%)`;
            handle.style.left = `${percentage}%`;
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });
    });
});
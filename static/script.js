// smooth scrolling
document.querySelectorAll('a[href^="#"]').forEach
(anchor=>{
    anchor.addEventListener('click',function(e){
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior:'smooth'
        });
    });
});

//Navbar scroll effect
window.addEventListener('scroll',()=>{
    const navbar=document.querySelector('.navbar');
    window.scrollY>50?
    navbar.style.backgroundColor='rgba(10,10,10,0.98)':
    navbar.style.backgroundColor='rgba(10,10,10,0.95)';
})

// Hamburger menu toggle
const hamburger = document.querySelector('.hamburger');
const navLinks = document.querySelector('.nav-links');

hamburger.addEventListener('click', () => {
    navLinks.classList.toggle('active');
    hamburger.classList.toggle('active');
});

// Close mobile menu when clicking on a link
document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', () => {
        navLinks.classList.remove('active');
        hamburger.classList.remove('active');
    });
});

// Close mobile menu when clicking outside
document.addEventListener('click', (e) => {
    if (!hamburger.contains(e.target) && !navLinks.contains(e.target)) {
        navLinks.classList.remove('active');
        hamburger.classList.remove('active');
    }
});

document.getElementById("aboutLink").addEventListener("click", function(event) {
    event.preventDefault(); // stop page scrolling
    const box = document.getElementById("aboutBox");
    box.classList.toggle("hidden");
});

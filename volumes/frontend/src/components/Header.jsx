import { useLocation } from 'react-router-dom'
import './Header.css'

function Header() {
    const location = useLocation();
    const pagesAuth = ['/login', '/signup', '/forgot-password', '/reset-password'];

    if (pagesAuth.includes(location.pathname)) {
        return null;
    }

    return (
        <header className="header">
            <h2>Hypertube</h2>
            <ul className='nav-list'>
                <div className='nav-left'>
                    <li><a href="/home">Home</a></li>
                    <li><input type='text' placeholder="Search..."></input></li>
                </div>
                <div className='nav-right'>
                    <li><a href="/home">Language</a></li>
                    <li><a href="/home">Disconnect</a></li>
                    <li><a href="/profile">Profile</a></li>
                </div>
            </ul>
        </header>
    );
}

export default Header;
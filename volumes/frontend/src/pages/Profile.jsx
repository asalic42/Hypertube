import './Profile.css'

function Profile() {
    // fetch le user avec api
    return (
        <div className="profile-page">
            <img src='titanic.jpg' alt='UserAvatar'></img>
            <p>user.photo</p>
            <p>user.username</p>
            <p>user.firstname</p>
            <p>user.lastname</p>
            <p>user.email</p>
            <button>Update email</button>
            <button>Update password</button>
            <button className='delete-button'>Delete account</button>
        </div>
    )
}

export default Profile;
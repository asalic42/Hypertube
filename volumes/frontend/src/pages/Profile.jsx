import './Profile.css'
import { Button } from "@/components/ui/button"

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
            <Button>Update email</Button>
            <Button>Update password</Button>
            <Button className='delete-Button'>Delete account</Button>
        </div>
    )
}

export default Profile;
import { Button } from "@/components/ui/button"
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSeparator,
  FieldSet,
  FieldTitle,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";

import defaultAvatar from '../../public/titanic.jpg'

function Profile() {
    // fetch le user avec api
    return (
        <FieldSet className="w-full max-w-sm">
            <Field className="flex justify-center items-center">
            <Avatar className="size-95 shrink-0">
                <AvatarImage src={defaultAvatar} alt="profile picture" />
                <AvatarFallback>A</AvatarFallback>
              {/* <AvatarImage src={user.profilePicture} alt={user.username} /> */}
              {/* <AvatarFallback>{user.username?.[0]?.toUpperCase()}</AvatarFallback> */}
            </Avatar>
            </Field>
        <FieldLegend className="w-full text-center">Profile</FieldLegend>
        <FieldDescription>Check or update your information</FieldDescription>
        <FieldSeparator />
        <FieldGroup>
            <Field>
            <FieldLabel htmlFor="firstname">First name</FieldLabel>
            <p className="text-sm text-muted-foreground">Anthony</p>
            </Field>
            <FieldSeparator />
            <Field>
            <FieldLabel htmlFor="lastname">Last name</FieldLabel>
            <p className="text-sm text-muted-foreground">Anthony</p>
            </Field>
            <FieldSeparator />
            <Field>
            <FieldLabel htmlFor="username">Username</FieldLabel>
            <p className="text-sm text-muted-foreground">Anthony</p>
            </Field>
            <FieldSeparator />
            <Field>
            <FieldLabel htmlFor="email">Email</FieldLabel>
            <p className="text-sm text-muted-foreground">Anthony</p>
            </Field>
            <FieldSeparator />
            <Field>
                <Button type="submit" size="icon">Update informations</Button>
                <Button type="submit" variant="destructive">Delete account</Button>
            </Field>
        </FieldGroup>
        </FieldSet>
        // <div className="profile-page">
        //     <img src='titanic.jpg' alt='UserAvatar'></img>
        //     <p>user.photo</p>
        //     <p>user.username</p>
        //     <p>user.firstname</p>
        //     <p>user.lastname</p>
        //     <p>user.email</p>
        //     <Button>Update email</Button>
        //     <Button>Update password</Button>
        //     <Button className='delete-Button'>Delete account</Button>
        // </div>
    )
}

export default Profile;
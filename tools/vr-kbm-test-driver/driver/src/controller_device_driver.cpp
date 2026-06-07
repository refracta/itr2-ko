//============ Copyright (c) Valve Corporation, All rights reserved. ============
#include "controller_device_driver.h"

#include "driverlog.h"
#include "vrmath.h"

#include <algorithm>
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

static vr::HmdMatrix34_t IdentityPoseOffset()
{
	vr::HmdMatrix34_t matrix{};
	matrix.m[ 0 ][ 0 ] = 1.0f;
	matrix.m[ 1 ][ 1 ] = 1.0f;
	matrix.m[ 2 ][ 2 ] = 1.0f;
	return matrix;
}

static bool IsKeyDown( int virtual_key )
{
	return ( GetAsyncKeyState( virtual_key ) & 0x8000 ) != 0;
}

static bool IsCharDown( char key )
{
	return IsKeyDown( static_cast< int >( key ) );
}

static float AxisValue( bool positive, bool negative )
{
	return ( positive ? 1.0f : 0.0f ) - ( negative ? 1.0f : 0.0f );
}

static bool GetMouseAim( float &yaw, float &pitch )
{
	POINT point{};
	if ( !GetCursorPos( &point ) )
		return false;

	RECT rect{};
	HWND game_window = FindWindowA( nullptr, "IntoTheRadius2," );
	if ( game_window != nullptr && GetWindowRect( game_window, &rect ) )
	{
		// The null HMD headset window can remain black, so use the visible game mirror for mouse aiming.
	}
	else
	{
		HWND headset_window = FindWindowA( nullptr, "Headset Window" );
		if ( headset_window != nullptr && GetWindowRect( headset_window, &rect ) )
		{
			// Fall back to the SteamVR headset window when the game mirror is not present.
		}
		else
		{
			rect.left = GetSystemMetrics( SM_XVIRTUALSCREEN );
			rect.top = GetSystemMetrics( SM_YVIRTUALSCREEN );
			rect.right = rect.left + GetSystemMetrics( SM_CXVIRTUALSCREEN );
			rect.bottom = rect.top + GetSystemMetrics( SM_CYVIRTUALSCREEN );
		}
	}

	const float width = static_cast< float >( std::max( 1L, rect.right - rect.left ) );
	const float height = static_cast< float >( std::max( 1L, rect.bottom - rect.top ) );
	const float x = std::clamp( ( static_cast< float >( point.x - rect.left ) / width - 0.5f ) * 2.0f, -1.0f, 1.0f );
	const float y = std::clamp( ( static_cast< float >( point.y - rect.top ) / height - 0.5f ) * 2.0f, -1.0f, 1.0f );

	yaw = -x * 0.95f;
	pitch = -y * 0.65f;
	return true;
}

static void UpdateButton( vr::VRInputComponentHandle_t touch, vr::VRInputComponentHandle_t click, bool pressed )
{
	vr::VRDriverInput()->UpdateBooleanComponent( touch, pressed, 0 );
	vr::VRDriverInput()->UpdateBooleanComponent( click, pressed, 0 );
}

static void UpdateTrigger( vr::VRInputComponentHandle_t value, vr::VRInputComponentHandle_t touch, vr::VRInputComponentHandle_t click, bool pressed )
{
	vr::VRDriverInput()->UpdateScalarComponent( value, pressed ? 1.0f : 0.0f, 0 );
	vr::VRDriverInput()->UpdateBooleanComponent( touch, pressed, 0 );
	vr::VRDriverInput()->UpdateBooleanComponent( click, pressed, 0 );
}

// Let's create some variables for strings used in getting settings.
// This is the section where all of the settings we want are stored. A section name can be anything,
// but if you want to store driver specific settings, it's best to namespace the section with the driver identifier
// ie "<my_driver>_<section>" to avoid collisions
static const char *my_controller_main_settings_section = "driver_simplecontroller";

// Individual right/left hand settings sections
static const char *my_controller_right_settings_section = "driver_simplecontroller_right_controller";
static const char *my_controller_left_settings_section = "driver_simplecontroller_left_controller";

// These are the keys we want to retrieve the values for in the settings
static const char *my_controller_settings_key_model_number = "mycontroller_model_number";
static const char *my_controller_settings_key_serial_number = "mycontroller_serial_number";


MyControllerDeviceDriver::MyControllerDeviceDriver( vr::ETrackedControllerRole role )
{
	// Set a member to keep track of whether we've activated yet or not
	is_active_ = false;

	// The constructor takes a role argument, that gives us information about if our controller is a left or right hand.
	// Let's store it for later use. We'll need it.
	my_controller_role_ = role;

	// We have our model number and serial number stored in SteamVR settings. We need to get them and do so here.
	// Other IVRSettings methods (to get int32, floats, bools) return the data, instead of modifying, but strings are
	// different.
	char model_number[ 1024 ];
	vr::VRSettings()->GetString( my_controller_main_settings_section, my_controller_settings_key_model_number, model_number, sizeof( model_number ) );
	my_controller_model_number_ = model_number;

	// Get our serial number depending on our "handedness"
	char serial_number[ 1024 ];
	vr::VRSettings()->GetString( my_controller_role_ == vr::TrackedControllerRole_LeftHand ? my_controller_left_settings_section : my_controller_right_settings_section,
		my_controller_settings_key_serial_number, serial_number, sizeof( serial_number ) );
	my_controller_serial_number_ = serial_number;

	// Here's an example of how to use our logging wrapper around IVRDriverLog
	// In SteamVR logs (SteamVR Hamburger Menu > Developer Settings > Web console) drivers have a prefix of
	// "<driver_name>:". You can search this in the top search bar to find the info that you've logged.
	DriverLog( "My Controller Model Number: %s", my_controller_model_number_.c_str() );
	DriverLog( "My Controller Serial Number: %s", my_controller_serial_number_.c_str() );
}

//-----------------------------------------------------------------------------
// Purpose: This is called by vrserver after our
//  IServerTrackedDeviceProvider calls IVRServerDriverHost::TrackedDeviceAdded.
//-----------------------------------------------------------------------------
vr::EVRInitError MyControllerDeviceDriver::Activate( uint32_t unObjectId )
{
	// Set an member to keep track of whether we've activated yet or not
	is_active_ = true;

	// Let's keep track of our device index. It'll be useful later.
	my_controller_index_ = unObjectId;

	// Properties are stored in containers, usually one container per device index. We need to get this container to set
	// The properties we want, so we call this to retrieve a handle to it.
	vr::PropertyContainerHandle_t container = vr::VRProperties()->TrackedDeviceToPropertyContainer( my_controller_index_ );

	// Let's begin setting up the properties now we've got our container.
	// A list of properties available is contained in vr::ETrackedDeviceProperty.

	// First, let's set the model number.
	vr::VRProperties()->SetStringProperty( container, vr::Prop_ModelNumber_String, my_controller_model_number_.c_str() );
	vr::VRProperties()->SetStringProperty( container, vr::Prop_ControllerType_String, "knuckles" );

	// Let's tell SteamVR our role which we received from the constructor earlier.
	vr::VRProperties()->SetInt32Property( container, vr::Prop_ControllerRoleHint_Int32, my_controller_role_ );


	// Now let's set up our inputs

	// This tells the UI what to show the user for bindings for this controller,
	// As well as what default bindings should be for legacy apps.
	// Note, we can use the wildcard {<driver_name>} to match the root folder location
	// of our driver.
	vr::VRProperties()->SetStringProperty( container, vr::Prop_InputProfilePath_String, "{simplecontroller}/input/mycontroller_profile.json" );

	// Let's set up handles for all of our components.
	// Even though these are also defined in our input profile,
	// We need to get handles to them to update the inputs.

	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/a/touch", &input_handles_[ MyComponent_a_touch ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/a/click", &input_handles_[ MyComponent_a_click ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/b/touch", &input_handles_[ MyComponent_b_touch ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/b/click", &input_handles_[ MyComponent_b_click ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/x/touch", &input_handles_[ MyComponent_x_touch ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/x/click", &input_handles_[ MyComponent_x_click ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/y/touch", &input_handles_[ MyComponent_y_touch ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/y/click", &input_handles_[ MyComponent_y_click ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/system/touch", &input_handles_[ MyComponent_system_touch ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/system/click", &input_handles_[ MyComponent_system_click ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/menu/touch", &input_handles_[ MyComponent_menu_touch ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/menu/click", &input_handles_[ MyComponent_menu_click ] );

	// Let's set up our trigger. We've defined it to have a value and click component.

	// CreateScalarComponent requires:
	// EVRScalarType - whether the device can give an absolute position, or just one relative to where it was last. We
	// can do it absolute.
	// EVRScalarUnits - whether the devices has two "sides", like a joystick. This makes the range of valid inputs -1
	// to 1. Otherwise, it's 0 to 1. We only have one "side", so ours is onesided.
	vr::VRDriverInput()->CreateScalarComponent( container, "/input/trigger/value", &input_handles_[ MyComponent_trigger_value ], vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedOneSided );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/trigger/touch", &input_handles_[ MyComponent_trigger_touch ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/trigger/click", &input_handles_[ MyComponent_trigger_click ] );
	vr::VRDriverInput()->CreateScalarComponent( container, "/input/grip/value", &input_handles_[ MyComponent_grip_value ], vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedOneSided );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/grip/touch", &input_handles_[ MyComponent_grip_touch ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/grip/click", &input_handles_[ MyComponent_grip_click ] );
	vr::VRDriverInput()->CreateScalarComponent( container, "/input/grip/force", &input_handles_[ MyComponent_grip_force ], vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedOneSided );
	vr::VRDriverInput()->CreateScalarComponent( container, "/input/joystick/x", &input_handles_[ MyComponent_joystick_x ], vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedTwoSided );
	vr::VRDriverInput()->CreateScalarComponent( container, "/input/joystick/y", &input_handles_[ MyComponent_joystick_y ], vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedTwoSided );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/joystick/touch", &input_handles_[ MyComponent_joystick_touch ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/joystick/click", &input_handles_[ MyComponent_joystick_click ] );
	vr::VRDriverInput()->CreateScalarComponent( container, "/input/thumbstick/x", &input_handles_[ MyComponent_thumbstick_x ], vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedTwoSided );
	vr::VRDriverInput()->CreateScalarComponent( container, "/input/thumbstick/y", &input_handles_[ MyComponent_thumbstick_y ], vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedTwoSided );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/thumbstick/touch", &input_handles_[ MyComponent_thumbstick_touch ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/thumbstick/click", &input_handles_[ MyComponent_thumbstick_click ] );
	vr::VRDriverInput()->CreateScalarComponent( container, "/input/trackpad/x", &input_handles_[ MyComponent_trackpad_x ], vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedTwoSided );
	vr::VRDriverInput()->CreateScalarComponent( container, "/input/trackpad/y", &input_handles_[ MyComponent_trackpad_y ], vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedTwoSided );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/trackpad/touch", &input_handles_[ MyComponent_trackpad_touch ] );
	vr::VRDriverInput()->CreateBooleanComponent( container, "/input/trackpad/click", &input_handles_[ MyComponent_trackpad_click ] );
	vr::VRDriverInput()->CreateScalarComponent( container, "/input/trackpad/force", &input_handles_[ MyComponent_trackpad_force ], vr::VRScalarType_Absolute, vr::VRScalarUnits_NormalizedOneSided );
	vr::VRDriverInput()->CreatePoseComponent( container, "/pose/raw", &input_handles_[ MyComponent_pose_raw ] );
	vr::VRDriverInput()->CreatePoseComponent( container, "/pose/openxr_aim", &input_handles_[ MyComponent_pose_openxr_aim ] );
	vr::VRDriverInput()->CreatePoseComponent( container, "/pose/openxr_grip", &input_handles_[ MyComponent_pose_openxr_grip ] );
	vr::VRDriverInput()->CreatePoseComponent( container, "/pose/tip", &input_handles_[ MyComponent_pose_tip ] );
	vr::VRDriverInput()->CreatePoseComponent( container, "/pose/grip", &input_handles_[ MyComponent_pose_grip ] );

	// Let's create our haptic component.
	// These are global across the device, and you can only have one per device.
	vr::VRDriverInput()->CreateHapticComponent( container, "/output/haptic", &input_handles_[ MyComponent_haptic ] );

	// We've activated everything successfully!
	// Let's tell SteamVR that by saying we don't have any errors.
	return vr::VRInitError_None;
}

//-----------------------------------------------------------------------------
// Purpose: If you're an HMD, this is where you would return an implementation
// of vr::IVRDisplayComponent, vr::IVRVirtualDisplay or vr::IVRDirectModeComponent.
//
// But this a simple example to demo for a controller, so we'll just return nullptr here.
//-----------------------------------------------------------------------------
void *MyControllerDeviceDriver::GetComponent( const char *pchComponentNameAndVersion )
{
	return nullptr;
}

//-----------------------------------------------------------------------------
// Purpose: This is called by vrserver when a debug request has been made from an application to the driver.
// What is in the response and request is up to the application and driver to figure out themselves.
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::DebugRequest( const char *pchRequest, char *pchResponseBuffer, uint32_t unResponseBufferSize )
{
	if ( unResponseBufferSize >= 1 )
		pchResponseBuffer[ 0 ] = 0;
}

//-----------------------------------------------------------------------------
// Purpose: This is never called by vrserver in recent OpenVR versions,
// but is useful for giving data to vr::VRServerDriverHost::TrackedDevicePoseUpdated.
//-----------------------------------------------------------------------------
vr::DriverPose_t MyControllerDeviceDriver::GetPose()
{
	// Let's retrieve the Hmd pose to base our controller pose off.

	// First, initialize the struct that we'll be submitting to the runtime to tell it we've updated our pose.
	vr::DriverPose_t pose = { 0 };

	// These need to be set to be valid quaternions. The device won't appear otherwise.
	pose.qWorldFromDriverRotation.w = 1.f;
	pose.qDriverFromHeadRotation.w = 1.f;

	vr::TrackedDevicePose_t hmd_pose{};

	// GetRawTrackedDevicePoses expects an array.
	// We only want the hmd pose, which is at index 0 of the array so we can just pass the struct in directly, instead of in an array
	vr::VRServerDriverHost()->GetRawTrackedDevicePoses( 0.f, &hmd_pose, 1 );

	// Get the position of the hmd from the 3x4 matrix GetRawTrackedDevicePoses returns
	const vr::HmdVector3_t hmd_position = HmdVector3_From34Matrix( hmd_pose.mDeviceToAbsoluteTracking );
	// Get the orientation of the hmd from the 3x4 matrix GetRawTrackedDevicePoses returns
	const vr::HmdQuaternion_t hmd_orientation = HmdQuaternion_FromMatrix( hmd_pose.mDeviceToAbsoluteTracking );

	const float aim_yaw = aim_yaw_.load();
	const float aim_pitch = aim_pitch_.load();

	// Keep the controller in front of the HMD and let the keyboard steer the aim ray.
	const vr::HmdQuaternion_t offset_orientation =
		HmdQuaternion_FromEulerAngles( aim_pitch, DEG_TO_RAD( 90.f ), aim_yaw );

	// Set the pose orientation to the hmd orientation with the offset applied.
	pose.qRotation = hmd_orientation * offset_orientation;

	const vr::HmdVector3_t offset_position = {
		my_controller_role_ == vr::TrackedControllerRole_LeftHand ? -0.15f : 0.15f, // translate the controller left/right 0.15m depending on its role
		0.1f + height_offset_.load(),												// shift it up a little to make it more in view
		-0.5f + depth_offset_.load(),												// put each controller 0.5m forward in front of the hmd so we can see it.
	};

	// Rotate our offset by the hmd quaternion (so the controllers are always facing towards us), and add then add the position of the hmd to put it into position.
	const vr::HmdVector3_t position = hmd_position + ( offset_position * hmd_orientation );

	// copy our position to our pose
	pose.vecPosition[ 0 ] = position.v[ 0 ];
	pose.vecPosition[ 1 ] = position.v[ 1 ];
	pose.vecPosition[ 2 ] = position.v[ 2 ];

	// The pose we provided is valid.
	// This should be set is
	pose.poseIsValid = true;

	// Our device is always connected.
	// In reality with physical devices, when they get disconnected,
	// set this to false and icons in SteamVR will be updated to show the device is disconnected
	pose.deviceIsConnected = true;

	// The state of our tracking. For our virtual device, it's always going to be ok,
	// but this can get set differently to inform the runtime about the state of the device's tracking
	// and update the icons to inform the user accordingly.
	pose.result = vr::TrackingResult_Running_OK;

	return pose;
}

void MyControllerDeviceDriver::MyPoseUpdateThread()
{
	while ( is_active_ )
	{
		// Inform the vrserver that our tracked device's pose has updated, giving it the pose returned by our GetPose().
		vr::VRServerDriverHost()->TrackedDevicePoseUpdated( my_controller_index_, GetPose(), sizeof( vr::DriverPose_t ) );

		// Update our pose every five milliseconds.
		// In reality, you should update the pose whenever you have new data from your device.
		std::this_thread::sleep_for( std::chrono::milliseconds( 5 ) );
	}
}

//-----------------------------------------------------------------------------
// Purpose: This is called by vrserver when the device should enter standby mode.
// The device should be put into whatever low power mode it has.
// We don't really have anything to do here, so let's just log something.
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::EnterStandby()
{
	DriverLog( "%s hand has been put on standby", my_controller_role_ == vr::TrackedControllerRole_LeftHand ? "Left" : "Right" );
}

//-----------------------------------------------------------------------------
// Purpose: This is called by vrserver when the device should deactivate.
// This is typically at the end of a session
// The device should free any resources it has allocated here.
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::Deactivate()
{
	// Let's join our pose thread that's running
	// by first checking then setting is_active_ to false to break out
	// of the while loop, if it's running, then call .join() on the thread
	if ( is_active_.exchange( false ) )
	{
		if ( my_pose_update_thread_.joinable() )
			my_pose_update_thread_.join();
	}

	// unassign our controller index (we don't want to be calling vrserver anymore after Deactivate() has been called
	my_controller_index_ = vr::k_unTrackedDeviceIndexInvalid;
}


//-----------------------------------------------------------------------------
// Purpose: This is called by our IServerTrackedDeviceProvider when its RunFrame() method gets called.
// It's not part of the ITrackedDeviceServerDriver interface, we created it ourselves.
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::MyRunFrame()
{
	const bool is_right = my_controller_role_ == vr::TrackedControllerRole_RightHand;

	if ( is_right )
	{
		float mouse_yaw = 0.0f;
		float mouse_pitch = 0.0f;
		if ( GetMouseAim( mouse_yaw, mouse_pitch ) )
		{
			aim_yaw_.store( mouse_yaw );
			aim_pitch_.store( mouse_pitch );
		}

		const int frame = debug_frame_.fetch_add( 1 );
		if ( frame % 300 == 0 )
		{
			DriverLog( "Right aim yaw=%.3f pitch=%.3f height=%.3f depth=%.3f", aim_yaw_.load(), aim_pitch_.load(), height_offset_.load(), depth_offset_.load() );
		}

		height_offset_.store( std::clamp( height_offset_.load() + AxisValue( IsCharDown( 'Y' ), IsCharDown( 'H' ) ) * 0.01f, -0.5f, 0.5f ) );
		depth_offset_.store( std::clamp( depth_offset_.load() + AxisValue( IsCharDown( 'U' ), IsCharDown( 'O' ) ) * 0.01f, -0.7f, 0.2f ) );

		if ( IsKeyDown( VK_HOME ) )
		{
			aim_yaw_.store( 0.0f );
			aim_pitch_.store( 0.0f );
			height_offset_.store( 0.0f );
			depth_offset_.store( 0.0f );
		}
	}

	const bool trigger = is_right && ( IsKeyDown( VK_RETURN ) || IsKeyDown( VK_LBUTTON ) );
	if ( is_right && last_trigger_.exchange( trigger ) != trigger )
	{
		DriverLog( "Right trigger %s", trigger ? "down" : "up" );
	}
	const bool grip = IsCharDown( 'Q' ) || IsCharDown( 'E' );
	const bool stick_click = IsKeyDown( VK_TAB );
	const bool primary = is_right ? IsKeyDown( VK_RETURN ) : IsCharDown( 'Z' );
	const bool secondary = is_right ? IsKeyDown( VK_BACK ) : IsCharDown( 'X' );
	const bool menu = !is_right && IsKeyDown( VK_F10 );
	const bool system = IsKeyDown( VK_F12 );

	const float left_stick_x = 0.0f;
	const float left_stick_y = AxisValue( IsCharDown( 'W' ), IsCharDown( 'S' ) );
	const float right_stick_x = AxisValue( IsCharDown( 'D' ) || IsKeyDown( VK_RIGHT ), IsCharDown( 'A' ) || IsKeyDown( VK_LEFT ) );
	const float right_stick_y = AxisValue( IsCharDown( 'W' ) || IsKeyDown( VK_UP ), IsCharDown( 'S' ) || IsKeyDown( VK_DOWN ) );
	const float stick_x = is_right ? right_stick_x : left_stick_x;
	const float stick_y = is_right ? right_stick_y : left_stick_y;
	const float trackpad_x = AxisValue( IsKeyDown( VK_F8 ), IsKeyDown( VK_F7 ) );
	const float trackpad_y = AxisValue( IsKeyDown( VK_F5 ), IsKeyDown( VK_F6 ) );
	const int stick_x_bucket = static_cast< int >( stick_x );
	const int stick_y_bucket = static_cast< int >( stick_y );
	const int previous_stick_x = last_stick_x_.exchange( stick_x_bucket );
	const int previous_stick_y = last_stick_y_.exchange( stick_y_bucket );
	if ( previous_stick_x != stick_x_bucket || previous_stick_y != stick_y_bucket )
	{
		DriverLog( "%s thumbstick x=%d y=%d", is_right ? "Right movement" : "Left forward candidate", stick_x_bucket, stick_y_bucket );
	}
	const bool stick_touch = stick_x != 0.0f || stick_y != 0.0f || stick_click;
	const float grip_force = grip ? 1.0f : 0.0f;
	const bool trackpad_touch = trackpad_x != 0.0f || trackpad_y != 0.0f;
	const bool trackpad_click = trackpad_touch;
	const float trackpad_force = trackpad_touch ? 1.0f : 0.0f;

	UpdateButton( input_handles_[ MyComponent_a_touch ], input_handles_[ MyComponent_a_click ], primary );
	UpdateButton( input_handles_[ MyComponent_b_touch ], input_handles_[ MyComponent_b_click ], secondary );
	UpdateButton( input_handles_[ MyComponent_x_touch ], input_handles_[ MyComponent_x_click ], !is_right && primary );
	UpdateButton( input_handles_[ MyComponent_y_touch ], input_handles_[ MyComponent_y_click ], !is_right && secondary );
	UpdateButton( input_handles_[ MyComponent_system_touch ], input_handles_[ MyComponent_system_click ], system );
	UpdateButton( input_handles_[ MyComponent_menu_touch ], input_handles_[ MyComponent_menu_click ], menu );
	UpdateTrigger( input_handles_[ MyComponent_trigger_value ], input_handles_[ MyComponent_trigger_touch ], input_handles_[ MyComponent_trigger_click ], trigger );
	UpdateTrigger( input_handles_[ MyComponent_grip_value ], input_handles_[ MyComponent_grip_touch ], input_handles_[ MyComponent_grip_click ], grip );
	vr::VRDriverInput()->UpdateScalarComponent( input_handles_[ MyComponent_grip_force ], grip_force, 0 );
	vr::VRDriverInput()->UpdateScalarComponent( input_handles_[ MyComponent_joystick_x ], stick_x, 0 );
	vr::VRDriverInput()->UpdateScalarComponent( input_handles_[ MyComponent_joystick_y ], stick_y, 0 );
	vr::VRDriverInput()->UpdateBooleanComponent( input_handles_[ MyComponent_joystick_touch ], stick_touch, 0 );
	vr::VRDriverInput()->UpdateBooleanComponent( input_handles_[ MyComponent_joystick_click ], stick_click, 0 );
	vr::VRDriverInput()->UpdateScalarComponent( input_handles_[ MyComponent_thumbstick_x ], stick_x, 0 );
	vr::VRDriverInput()->UpdateScalarComponent( input_handles_[ MyComponent_thumbstick_y ], stick_y, 0 );
	vr::VRDriverInput()->UpdateBooleanComponent( input_handles_[ MyComponent_thumbstick_touch ], stick_touch, 0 );
	vr::VRDriverInput()->UpdateBooleanComponent( input_handles_[ MyComponent_thumbstick_click ], stick_click, 0 );
	vr::VRDriverInput()->UpdateScalarComponent( input_handles_[ MyComponent_trackpad_x ], trackpad_x, 0 );
	vr::VRDriverInput()->UpdateScalarComponent( input_handles_[ MyComponent_trackpad_y ], trackpad_y, 0 );
	vr::VRDriverInput()->UpdateBooleanComponent( input_handles_[ MyComponent_trackpad_touch ], trackpad_touch, 0 );
	vr::VRDriverInput()->UpdateBooleanComponent( input_handles_[ MyComponent_trackpad_click ], trackpad_click, 0 );
	vr::VRDriverInput()->UpdateScalarComponent( input_handles_[ MyComponent_trackpad_force ], trackpad_force, 0 );

	const vr::HmdMatrix34_t identity = IdentityPoseOffset();
	vr::VRDriverInput()->UpdatePoseComponent( input_handles_[ MyComponent_pose_raw ], &identity, 0 );
	vr::VRDriverInput()->UpdatePoseComponent( input_handles_[ MyComponent_pose_openxr_aim ], &identity, 0 );
	vr::VRDriverInput()->UpdatePoseComponent( input_handles_[ MyComponent_pose_openxr_grip ], &identity, 0 );
	vr::VRDriverInput()->UpdatePoseComponent( input_handles_[ MyComponent_pose_tip ], &identity, 0 );
	vr::VRDriverInput()->UpdatePoseComponent( input_handles_[ MyComponent_pose_grip ], &identity, 0 );

	vr::VRServerDriverHost()->TrackedDevicePoseUpdated( my_controller_index_, GetPose(), sizeof( vr::DriverPose_t ) );
}


//-----------------------------------------------------------------------------
// Purpose: This is called by our IServerTrackedDeviceProvider when it pops an event off the event queue.
// It's not part of the ITrackedDeviceServerDriver interface, we created it ourselves.
//-----------------------------------------------------------------------------
void MyControllerDeviceDriver::MyProcessEvent( const vr::VREvent_t &vrevent )
{
	switch ( vrevent.eventType )
	{
		// Listen for haptic events
		case vr::VREvent_Input_HapticVibration:
		{
			// We now need to make sure that the event was intended for this device.
			// So let's compare handles of the event and our haptic component

			if ( vrevent.data.hapticVibration.componentHandle == input_handles_[ MyComponent_haptic ] )
			{
				// The event was intended for us!
				// To convert the data to a pulse, see the docs.
				// For this driver, we'll just print the values.

				float duration = vrevent.data.hapticVibration.fDurationSeconds;
				float frequency = vrevent.data.hapticVibration.fFrequency;
				float amplitude = vrevent.data.hapticVibration.fAmplitude;

				DriverLog( "Haptic event triggered for %s hand. Duration: %.2f, Frequency: %.2f, Amplitude: %.2f", my_controller_role_ == vr::TrackedControllerRole_LeftHand ? "left" : "right",
					duration, frequency, amplitude );
			}
			break;
		}
		default:
			break;
	}
}

//-----------------------------------------------------------------------------
// Purpose: Our IServerTrackedDeviceProvider needs our serial number to add us to vrserver.
// It's not part of the ITrackedDeviceServerDriver interface, we created it ourselves.
//-----------------------------------------------------------------------------
const std::string &MyControllerDeviceDriver::MyGetSerialNumber()
{
	return my_controller_serial_number_;
}

//============ Copyright (c) Valve Corporation, All rights reserved. ============
#include "hmd_device_driver.h"

#include "driverlog.h"
#include "vrmath.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>

static const char *hmd_settings_section = "driver_simplecontroller_hmd";
static const char *display_settings_section = "simplecontroller_display";
static std::atomic< bool > g_forward_key_down{ false };
static std::atomic< bool > g_backward_key_down{ false };

static bool WindowTitleContains( HWND hwnd, const char *needle )
{
	char title[ 256 ]{};
	if ( hwnd == nullptr || GetWindowTextA( hwnd, title, sizeof( title ) ) <= 0 )
		return false;

	return std::strstr( title, needle ) != nullptr;
}

static bool IsTargetForeground()
{
	HWND foreground = GetForegroundWindow();
	return foreground != nullptr && ( WindowTitleContains( foreground, "Headset Window" ) || WindowTitleContains( foreground, "IntoTheRadius2" ) );
}

static LRESULT CALLBACK KeyboardHookProc( int code, WPARAM w_param, LPARAM l_param )
{
	if ( code == HC_ACTION )
	{
		const auto *keyboard = reinterpret_cast< const KBDLLHOOKSTRUCT * >( l_param );
		const bool is_key_down_event = w_param == WM_KEYDOWN || w_param == WM_SYSKEYDOWN;
		const bool is_key_up_event = w_param == WM_KEYUP || w_param == WM_SYSKEYUP;
		const bool is_blocked_key = keyboard != nullptr
			&& ( keyboard->vkCode == VK_ESCAPE || keyboard->vkCode == VK_SPACE || keyboard->vkCode == 'W' || keyboard->vkCode == 'S' );
		const bool is_key_event = is_key_down_event || is_key_up_event;
		const bool is_target_foreground = IsTargetForeground();
		if ( keyboard != nullptr && is_key_event && is_target_foreground )
		{
			if ( keyboard->vkCode == 'W' )
				g_forward_key_down.store( is_key_down_event );
			else if ( keyboard->vkCode == 'S' )
				g_backward_key_down.store( is_key_down_event );
		}
		if ( is_blocked_key && is_key_event && is_target_foreground )
			return 1;
	}

	return CallNextHookEx( nullptr, code, w_param, l_param );
}

static bool GetTargetWindowRect( RECT &rect )
{
	HWND foreground = GetForegroundWindow();
	if ( IsTargetForeground() )
	{
		RECT client{};
		if ( GetClientRect( foreground, &client ) )
		{
			POINT top_left{ client.left, client.top };
			POINT bottom_right{ client.right, client.bottom };
			ClientToScreen( foreground, &top_left );
			ClientToScreen( foreground, &bottom_right );
			rect = { top_left.x, top_left.y, bottom_right.x, bottom_right.y };
			return true;
		}
	}

	return false;
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

MyHMDDeviceDriver::MyHMDDeviceDriver()
{
	char model_number[ 1024 ]{};
	vr::VRSettings()->GetString( hmd_settings_section, "model_number", model_number, sizeof( model_number ) );
	model_number_ = model_number[ 0 ] != '\0' ? model_number : "MouseHMD";

	char serial_number[ 1024 ]{};
	vr::VRSettings()->GetString( hmd_settings_section, "serial_number", serial_number, sizeof( serial_number ) );
	serial_number_ = serial_number[ 0 ] != '\0' ? serial_number : "MouseHMDSerial";

	MyHMDDisplayDriverConfiguration display_configuration{};
	display_configuration.window_x = vr::VRSettings()->GetInt32( display_settings_section, "window_x" );
	display_configuration.window_y = vr::VRSettings()->GetInt32( display_settings_section, "window_y" );
	display_configuration.window_width = vr::VRSettings()->GetInt32( display_settings_section, "window_width" );
	display_configuration.window_height = vr::VRSettings()->GetInt32( display_settings_section, "window_height" );
	display_configuration.render_width = vr::VRSettings()->GetInt32( display_settings_section, "render_width" );
	display_configuration.render_height = vr::VRSettings()->GetInt32( display_settings_section, "render_height" );

	if ( display_configuration.window_width <= 0 )
		display_configuration.window_width = 1280;
	if ( display_configuration.window_height <= 0 )
		display_configuration.window_height = 720;
	if ( display_configuration.render_width <= 0 )
		display_configuration.render_width = 1280;
	if ( display_configuration.render_height <= 0 )
		display_configuration.render_height = 720;

	display_component_ = std::make_unique< MyHMDDisplayComponent >( display_configuration );
	DriverLog( "Mouse HMD Model Number: %s", model_number_.c_str() );
	DriverLog( "Mouse HMD Serial Number: %s", serial_number_.c_str() );
}

vr::EVRInitError MyHMDDeviceDriver::Activate( uint32_t unObjectId )
{
	device_index_ = unObjectId;
	is_active_ = true;

	vr::PropertyContainerHandle_t container = vr::VRProperties()->TrackedDeviceToPropertyContainer( device_index_ );
	vr::VRProperties()->SetStringProperty( container, vr::Prop_ModelNumber_String, model_number_.c_str() );
	vr::VRProperties()->SetStringProperty( container, vr::Prop_ManufacturerName_String, "Codex" );

	const float ipd = vr::VRSettings()->GetFloat( vr::k_pch_SteamVR_Section, vr::k_pch_SteamVR_IPD_Float );
	vr::VRProperties()->SetFloatProperty( container, vr::Prop_UserIpdMeters_Float, ipd > 0.0f ? ipd : 0.063f );
	vr::VRProperties()->SetFloatProperty( container, vr::Prop_DisplayFrequency_Float, 0.0f );
	vr::VRProperties()->SetFloatProperty( container, vr::Prop_UserHeadToEyeDepthMeters_Float, 0.0f );
	vr::VRProperties()->SetFloatProperty( container, vr::Prop_SecondsFromVsyncToPhotons_Float, 0.11f );
	vr::VRProperties()->SetBoolProperty( container, vr::Prop_IsOnDesktop_Bool, false );
	vr::VRProperties()->SetBoolProperty( container, vr::Prop_DisplayDebugMode_Bool, true );
	vr::VRProperties()->SetInt32Property( container, vr::Prop_ExpectedControllerCount_Int32, 2 );
	vr::VRProperties()->SetStringProperty( container, vr::Prop_ExpectedControllerType_String, "knuckles" );

	pose_update_thread_ = std::thread( &MyHMDDeviceDriver::MyPoseUpdateThread, this );
	keyboard_filter_active_.store( true );
	keyboard_filter_thread_ = std::thread( &MyHMDDeviceDriver::KeyboardFilterThread, this );

	return vr::VRInitError_None;
}

void *MyHMDDeviceDriver::GetComponent( const char *pchComponentNameAndVersion )
{
	if ( std::strcmp( pchComponentNameAndVersion, vr::IVRDisplayComponent_Version ) == 0 )
		return display_component_.get();

	return nullptr;
}

void MyHMDDeviceDriver::DebugRequest( const char *pchRequest, char *pchResponseBuffer, uint32_t unResponseBufferSize )
{
	if ( unResponseBufferSize >= 1 )
		pchResponseBuffer[ 0 ] = 0;
}

vr::DriverPose_t MyHMDDeviceDriver::GetPose()
{
	vr::DriverPose_t pose = { 0 };
	pose.qWorldFromDriverRotation.w = 1.0f;
	pose.qDriverFromHeadRotation.w = 1.0f;
	pose.qRotation = HmdQuaternion_FromEulerAngles( DEG_TO_RAD( 180.0f ), pitch_.load(), yaw_.load() );
	pose.vecPosition[ 0 ] = pos_x_.load();
	pose.vecPosition[ 1 ] = height_offset_.load();
	pose.vecPosition[ 2 ] = pos_z_.load();
	pose.poseIsValid = true;
	pose.deviceIsConnected = true;
	pose.result = vr::TrackingResult_Running_OK;
	pose.shouldApplyHeadModel = false;
	return pose;
}

void MyHMDDeviceDriver::MyPoseUpdateThread()
{
	while ( is_active_ )
	{
		vr::VRServerDriverHost()->TrackedDevicePoseUpdated( device_index_, GetPose(), sizeof( vr::DriverPose_t ) );
		std::this_thread::sleep_for( std::chrono::milliseconds( 5 ) );
	}
}

void MyHMDDeviceDriver::EnterStandby()
{
	DriverLog( "Mouse HMD has been put into standby." );
}

void MyHMDDeviceDriver::Deactivate()
{
	if ( is_active_.exchange( false ) && pose_update_thread_.joinable() )
		pose_update_thread_.join();

	keyboard_filter_active_.store( false );
	const uint32_t keyboard_thread_id = keyboard_filter_thread_id_.load();
	if ( keyboard_thread_id != 0 )
		PostThreadMessageA( keyboard_thread_id, WM_QUIT, 0, 0 );
	if ( keyboard_filter_thread_.joinable() )
		keyboard_filter_thread_.join();

	device_index_ = vr::k_unTrackedDeviceIndexInvalid;
}

void MyHMDDeviceDriver::KeyboardFilterThread()
{
	MSG msg{};
	PeekMessageA( &msg, nullptr, WM_USER, WM_USER, PM_NOREMOVE );
	keyboard_filter_thread_id_.store( GetCurrentThreadId() );

	HMODULE module = nullptr;
	GetModuleHandleExA( GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
		reinterpret_cast< LPCSTR >( &KeyboardHookProc ), &module );
	HHOOK hook = SetWindowsHookExA( WH_KEYBOARD_LL, KeyboardHookProc, module, 0 );
	DriverLog( "ESC/Space/W/S keyboard filter %s", hook != nullptr ? "enabled" : "failed" );

	while ( keyboard_filter_active_.load() )
	{
		const BOOL result = GetMessageA( &msg, nullptr, 0, 0 );
		if ( result <= 0 )
			break;
		TranslateMessage( &msg );
		DispatchMessageA( &msg );
	}

	if ( hook != nullptr )
		UnhookWindowsHookEx( hook );
	keyboard_filter_thread_id_.store( 0 );
	g_forward_key_down.store( false );
	g_backward_key_down.store( false );
	DriverLog( "ESC/Space/W/S keyboard filter disabled" );
}

void MyHMDDeviceDriver::UpdateMouseLook()
{
	const bool f9_is_down = IsKeyDown( VK_F9 );
	const bool f9_was_down = f9_was_down_.exchange( f9_is_down );
	if ( f9_is_down && !f9_was_down )
	{
		const bool enabled = !mouse_capture_enabled_.load();
		mouse_capture_enabled_.store( enabled );
		DriverLog( "Mouse capture %s", enabled ? "enabled" : "disabled" );
	}

	if ( IsKeyDown( VK_MENU ) || IsKeyDown( VK_LWIN ) || IsKeyDown( VK_RWIN ) )
	{
		if ( mouse_capture_enabled_.exchange( false ) )
			DriverLog( "Mouse capture disabled by release key" );
		return;
	}

	if ( !mouse_capture_enabled_.load() )
		return;

	RECT rect{};
	if ( !GetTargetWindowRect( rect ) )
		return;

	const int width = std::max( 1L, rect.right - rect.left );
	const int height = std::max( 1L, rect.bottom - rect.top );
	const int center_x = rect.left + width / 2;
	const int center_y = rect.top + height / 2;

	POINT point{};
	if ( !GetCursorPos( &point ) )
		return;

	const int dx = point.x - center_x;
	const int dy = point.y - center_y;
	if ( dx == 0 && dy == 0 )
		return;

	constexpr float sensitivity = 0.0022f;
	yaw_.store( yaw_.load() + static_cast< float >( dx ) * sensitivity );
	pitch_.store( std::clamp( pitch_.load() + static_cast< float >( dy ) * sensitivity, -1.25f, 1.25f ) );

	SetCursorPos( center_x, center_y );
}

void MyHMDDeviceDriver::MyRunFrame()
{
	static auto last_move_time = std::chrono::steady_clock::now();
	const auto now = std::chrono::steady_clock::now();
	float dt = std::chrono::duration< float >( now - last_move_time ).count();
	last_move_time = now;
	dt = std::clamp( dt, 0.0f, 0.05f );

	if ( IsKeyDown( VK_HOME ) )
	{
		yaw_.store( 0.0f );
		pitch_.store( 0.0f );
		pos_x_.store( 0.0f );
		pos_z_.store( 0.0f );
		height_offset_.store( 0.0f );
		g_forward_key_down.store( false );
		g_backward_key_down.store( false );
		mouse_capture_enabled_.store( true );
	}

	const float height_delta = AxisValue( IsKeyDown( VK_PRIOR ), IsKeyDown( VK_NEXT ) ) * 0.005f;
	if ( height_delta != 0.0f )
	{
		height_offset_.store( std::clamp( height_offset_.load() + height_delta, -0.8f, 0.8f ) );
	}

	const bool is_target_foreground = IsTargetForeground();
	if ( !is_target_foreground )
	{
		g_forward_key_down.store( false );
		g_backward_key_down.store( false );
	}

	const bool forward_down = is_target_foreground && ( g_forward_key_down.load() || IsCharDown( 'W' ) );
	const bool backward_down = is_target_foreground && ( g_backward_key_down.load() || IsCharDown( 'S' ) );
	const float forward_axis = AxisValue( forward_down, backward_down );
	if ( forward_axis != 0.0f )
	{
		constexpr float movement_speed_mps = 2.0f;
		const float yaw = yaw_.load();
		const float distance = forward_axis * movement_speed_mps * dt;
		pos_x_.store( pos_x_.load() - std::sin( yaw ) * distance );
		pos_z_.store( pos_z_.load() - std::cos( yaw ) * distance );
	}

	const int frame = height_log_frame_.fetch_add( 1 );
	if ( frame % 300 == 0 )
	{
		DriverLog( "Mouse HMD position x=%.2f z=%.2f height %.2fm", pos_x_.load(), pos_z_.load(), height_offset_.load() );
	}

	UpdateMouseLook();
	vr::VRServerDriverHost()->TrackedDevicePoseUpdated( device_index_, GetPose(), sizeof( vr::DriverPose_t ) );
}

void MyHMDDeviceDriver::MyProcessEvent( const vr::VREvent_t &vrevent )
{
}

const std::string &MyHMDDeviceDriver::MyGetSerialNumber()
{
	return serial_number_;
}

MyHMDDisplayComponent::MyHMDDisplayComponent( const MyHMDDisplayDriverConfiguration &config )
	: config_( config )
{
}

bool MyHMDDisplayComponent::IsDisplayOnDesktop()
{
	return true;
}

bool MyHMDDisplayComponent::IsDisplayRealDisplay()
{
	return false;
}

void MyHMDDisplayComponent::GetRecommendedRenderTargetSize( uint32_t *pnWidth, uint32_t *pnHeight )
{
	*pnWidth = config_.render_width;
	*pnHeight = config_.render_height;
}

void MyHMDDisplayComponent::GetEyeOutputViewport( vr::EVREye eEye, uint32_t *pnX, uint32_t *pnY, uint32_t *pnWidth, uint32_t *pnHeight )
{
	*pnY = 0;
	*pnWidth = config_.window_width / 2;
	*pnHeight = config_.window_height;
	*pnX = eEye == vr::Eye_Left ? 0 : config_.window_width / 2;
}

void MyHMDDisplayComponent::GetProjectionRaw( vr::EVREye eEye, float *pfLeft, float *pfRight, float *pfTop, float *pfBottom )
{
	*pfLeft = -1.0f;
	*pfRight = 1.0f;
	*pfTop = -1.0f;
	*pfBottom = 1.0f;
}

vr::DistortionCoordinates_t MyHMDDisplayComponent::ComputeDistortion( vr::EVREye eEye, float fU, float fV )
{
	vr::DistortionCoordinates_t coordinates{};
	coordinates.rfBlue[ 0 ] = fU;
	coordinates.rfBlue[ 1 ] = fV;
	coordinates.rfGreen[ 0 ] = fU;
	coordinates.rfGreen[ 1 ] = fV;
	coordinates.rfRed[ 0 ] = fU;
	coordinates.rfRed[ 1 ] = fV;
	return coordinates;
}

void MyHMDDisplayComponent::GetWindowBounds( int32_t *pnX, int32_t *pnY, uint32_t *pnWidth, uint32_t *pnHeight )
{
	*pnX = config_.window_x;
	*pnY = config_.window_y;
	*pnWidth = config_.window_width;
	*pnHeight = config_.window_height;
}

bool MyHMDDisplayComponent::ComputeInverseDistortion( vr::HmdVector2_t *pResult, vr::EVREye eEye, uint32_t unChannel, float fU, float fV )
{
	if ( pResult == nullptr )
		return false;

	pResult->v[ 0 ] = std::clamp( fU, 0.0f, 1.0f );
	pResult->v[ 1 ] = std::clamp( fV, 0.0f, 1.0f );
	return true;
}

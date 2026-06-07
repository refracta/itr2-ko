//============ Copyright (c) Valve Corporation, All rights reserved. ============
#pragma once

#include <array>
#include <string>

#include "openvr_driver.h"
#include <atomic>
#include <thread>

enum MyComponent
{
	MyComponent_a_touch,
	MyComponent_a_click,
	MyComponent_b_touch,
	MyComponent_b_click,
	MyComponent_x_touch,
	MyComponent_x_click,
	MyComponent_y_touch,
	MyComponent_y_click,
	MyComponent_system_touch,
	MyComponent_system_click,
	MyComponent_menu_touch,
	MyComponent_menu_click,
	MyComponent_trigger_value,
	MyComponent_trigger_touch,
	MyComponent_trigger_click,
	MyComponent_grip_value,
	MyComponent_grip_touch,
	MyComponent_grip_click,
	MyComponent_grip_force,
	MyComponent_joystick_x,
	MyComponent_joystick_y,
	MyComponent_joystick_touch,
	MyComponent_joystick_click,
	MyComponent_thumbstick_x,
	MyComponent_thumbstick_y,
	MyComponent_thumbstick_touch,
	MyComponent_thumbstick_click,
	MyComponent_trackpad_x,
	MyComponent_trackpad_y,
	MyComponent_trackpad_touch,
	MyComponent_trackpad_click,
	MyComponent_trackpad_force,
	MyComponent_pose_raw,
	MyComponent_pose_openxr_aim,
	MyComponent_pose_openxr_grip,
	MyComponent_pose_tip,
	MyComponent_pose_grip,
	MyComponent_haptic,

	MyComponent_MAX
};

//-----------------------------------------------------------------------------
// Purpose: Represents a single tracked device in the system.
// What this device actually is (controller, hmd) depends on the
// properties you set within the device (see implementation of Activate)
//-----------------------------------------------------------------------------
class MyControllerDeviceDriver : public vr::ITrackedDeviceServerDriver
{
public:
	MyControllerDeviceDriver( vr::ETrackedControllerRole role );

	vr::EVRInitError Activate( uint32_t unObjectId ) override;

	void EnterStandby() override;

	void *GetComponent( const char *pchComponentNameAndVersion ) override;

	void DebugRequest( const char *pchRequest, char *pchResponseBuffer, uint32_t unResponseBufferSize ) override;

	vr::DriverPose_t GetPose() override;

	void Deactivate() override;

	// ----- Functions we declare ourselves below -----

	const std::string &MyGetSerialNumber();

	void MyRunFrame();
	void MyProcessEvent( const vr::VREvent_t &vrevent );

	void MyPoseUpdateThread();

private:
	std::atomic< vr::TrackedDeviceIndex_t > my_controller_index_;

	vr::ETrackedControllerRole my_controller_role_;

	std::string my_controller_model_number_;
	std::string my_controller_serial_number_;

	std::array< vr::VRInputComponentHandle_t, MyComponent_MAX > input_handles_;

	std::atomic< bool > is_active_;
	std::thread my_pose_update_thread_;
	std::atomic< float > aim_yaw_{ 0.0f };
	std::atomic< float > aim_pitch_{ 0.0f };
	std::atomic< float > height_offset_{ 0.0f };
	std::atomic< float > depth_offset_{ 0.0f };
	std::atomic< bool > last_trigger_{ false };
	std::atomic< int > last_stick_x_{ 0 };
	std::atomic< int > last_stick_y_{ 0 };
	std::atomic< int > debug_frame_{ 0 };
};

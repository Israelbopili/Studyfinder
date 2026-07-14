import React, { useState, useEffect } from 'react';
import api from '../../api';

const Courses = () => {
  const [courses, setCourses] = useState([]);
  const [myCourses, setMyCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [coursesRes, myCoursesRes] = await Promise.all([
        api.get('/courses/'),
        api.get('/students/my-courses')
      ]);
      setCourses(coursesRes.data || []);
      setMyCourses(myCoursesRes.data || []);
    } catch (error) {
      console.error('Error fetching courses:', error);
    } finally {
      setLoading(false);
    }
  };

  const enroll = async (courseId) => {
    try {
      await api.post(`/students/enroll/${courseId}`);
      await fetchData();
      alert('Successfully enrolled!');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to enroll');
    }
  };

  const unenroll = async (courseId) => {
    try {
      await api.delete(`/students/unenroll/${courseId}`);
      await fetchData();
      alert('Successfully unenrolled');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to unenroll');
    }
  };

  const filteredCourses = courses.filter(c => 
    c.course_name.toLowerCase().includes(search.toLowerCase()) ||
    c.course_code.toLowerCase().includes(search.toLowerCase())
  );

  const isEnrolled = (courseId) => myCourses.some(c => c.course_id === courseId);

  if (loading) {
    return <div className="loading">Loading courses...</div>;
  }

  return (
    <div>
      <div className="section-header">
        <h2>Courses</h2>
        <input
          type="text"
          placeholder="🔍 Search courses..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="search-input"
        />
      </div>

      <div className="courses-grid">
        {filteredCourses.map((course) => (
          <div key={course.course_id} className="course-card">
            <h3>{course.course_code}</h3>
            <p>{course.course_name}</p>
            <p className="meta">{course.department || 'No department'}</p>
            {isEnrolled(course.course_id) ? (
              <button className="unenroll-btn" onClick={() => unenroll(course.course_id)}>
                ✅ Enrolled
              </button>
            ) : (
              <button className="enroll-btn" onClick={() => enroll(course.course_id)}>
                Enroll
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default Courses;